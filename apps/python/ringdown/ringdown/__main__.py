from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

from ringdown import report
from ringdown.adapter import adapt
from ringdown.audit import (
    append_record,
    attempt_record,
    chain_checks,
    head,
    intent_record,
    verdict_record,
    verification_record,
)
from ringdown.calle import (
    LOOPBACK_HOSTS,
    McpClient,
    RestClient,
    UntrustedHost,
    assert_trusted_base_url,
)
from ringdown.escalate import Attempt, LadderResult, run_ladder
from ringdown.exits import (
    EXIT_ACKNOWLEDGED,
    EXIT_UNKNOWN,
    EXIT_USAGE,
    reconcile,
    settle,
    verifiable,
)
from ringdown.incident import (
    Incident,
    IncidentError,
    Rung,
    load_incident,
    load_rotation,
    parse_incident,
    read_json,
    resolve_ladder,
    unstaffed_scopes,
)
from ringdown.script import call_payload, call_task, idempotency_key
from ringdown.checks import Check, all_checks, render_blocks
from ringdown.verify import verify_ladder

CONFIRMATION = "place real calls"
DEFAULT_BASE_URL = "https://api.heycall-e.com"
DEFAULT_MCP_URL = "https://seleven-mcp-sg.airudder.com/mcp/openagent_oauth"
WINDOW_SLACK = timedelta(seconds=60)


def emit(*lines: str) -> None:
    for line in lines:
        print(line)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ringdown")
    commands = parser.add_subparsers(dest="command")

    def with_files(name: str) -> argparse.ArgumentParser:
        command = commands.add_parser(name)
        command.add_argument("--incident", type=Path, required=True)
        command.add_argument("--rotation", type=Path, required=True)
        return command

    with_files("preview")
    run = with_files("run")
    run.add_argument("--ledger", type=Path, required=True)
    run.add_argument("--confirm", default="")
    run.add_argument("--base-url", default=DEFAULT_BASE_URL)
    run.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    run.add_argument("--allow-host", action="append", default=[])

    verify = commands.add_parser("verify")
    verify.add_argument("--ledger", type=Path, required=True)

    adapt_command = commands.add_parser("adapt")
    adapt_command.add_argument("--payload", type=Path, required=True)
    adapt_command.add_argument("--mapping", type=Path, required=True)
    adapt_command.add_argument("--out", type=Path)
    return parser


def _ladder(incident: Incident, rotation: Path, moment: datetime) -> tuple[Rung, ...]:
    rungs = resolve_ladder(incident, load_rotation(rotation), moment)
    for scope in unstaffed_scopes(incident, rungs):
        emit(f"note: scope {scope} has nobody on call and was skipped")
    return rungs


def preview(args: argparse.Namespace) -> int:
    incident = load_incident(args.incident)
    rungs = _ladder(incident, args.rotation, datetime.now(UTC))
    payload = call_payload(incident, rungs[0], 1)
    emit(*report.header_lines(incident, rungs))
    emit(f"idempotency key {idempotency_key(payload)}", "", call_task(incident, rungs[0]))
    return EXIT_ACKNOWLEDGED


def _verify(
    mcp: McpClient, incident: Incident, result: LadderResult, start: datetime
) -> list[Check]:
    window = (start - WINDOW_SLACK, datetime.now(UTC) + WINDOW_SLACK)
    blocks = verify_ladder(mcp, incident.id, result, window)
    emit("", render_blocks(blocks))
    return all_checks(blocks)


def run(args: argparse.Namespace) -> int:
    if args.confirm != CONFIRMATION:
        emit(f"refusing to place calls without --confirm {CONFIRMATION!r}")
        return EXIT_USAGE
    api_key = os.environ.get("CALLE_API_KEY", "")
    if not api_key:
        emit("CALLE_API_KEY is not set in the environment")
        return EXIT_USAGE
    allowed = frozenset(args.allow_host)
    base_url = assert_trusted_base_url(args.base_url, allowed)
    mcp_url = assert_trusted_base_url(args.mcp_url, allowed)
    rest_host = urlparse(base_url).hostname or ""
    mcp_host = urlparse(mcp_url).hostname or ""
    if rest_host == mcp_host:
        if mcp_host not in LOOPBACK_HOSTS:
            emit(f"refusing to verify {mcp_host} against itself: the second channel is the first one")
            return EXIT_USAGE
        emit(f"note: both channels are {mcp_host}, so this run cannot prove they are two")
    incident = load_incident(args.incident)
    start = datetime.now(UTC)
    rungs = _ladder(incident, args.rotation, start)
    emit(*report.header_lines(incident, rungs))

    total = len(rungs)

    def watch(position: int, rung: Rung, attempt: Attempt | None) -> None:
        if attempt is None:
            emit(report.attempt_header(position, total, rung))
            return
        append_record(args.ledger, attempt_record(attempt, incident.id))
        emit(*report.attempt_lines(attempt, incident.policy), "")

    def announce(attempt_id: str, key: str, rung: Rung) -> None:
        append_record(args.ledger, intent_record(incident.id, attempt_id, key, rung))

    result = run_ladder(
        RestClient(base_url, api_key, allowed_hosts=allowed),
        incident,
        rungs,
        log=lambda line: emit(report.progress_line(line)),
        watch=watch,
        announce=announce,
    )
    append_record(args.ledger, verdict_record(incident.id, result))
    emit(*report.verdict_lines(result))

    checks: list[Check] = []
    if verifiable(result.verdict, result.placed):
        mcp_key = os.environ.get("CALLE_MCP_TOKEN", "")
        mcp = McpClient(mcp_url, mcp_key, allowed_hosts=allowed)
        checks = _verify(mcp, incident, result, start)
        append_record(
            args.ledger,
            verification_record(incident.id, checks, rest_host=rest_host, mcp_host=mcp_host),
        )

    code = settle(result.verdict, result.placed, checks)
    if code == EXIT_UNKNOWN:
        emit(*report.unknown_lines(result))
    elif code == EXIT_USAGE:
        emit(*report.NOTHING_PLACED)
    elif code in report.ADVICE and result.verdict == "acknowledged":
        emit("", *report.ADVICE[code])
    emit("", *report.ledger_lines(*head(args.ledger), result))
    return code


def verify(args: argparse.Namespace) -> int:
    if not args.ledger.exists():
        raise IncidentError(f"no ledger file at {args.ledger}")
    checks = chain_checks(args.ledger)
    emit(render_blocks([(f"Ledger {args.ledger}", checks)]))
    return reconcile(EXIT_ACKNOWLEDGED, checks)


def adapt_command(args: argparse.Namespace) -> int:
    mapped = adapt(read_json(args.payload, "payload"), read_json(args.mapping, "field mapping"))
    parse_incident(mapped)
    rendered = json.dumps(mapped, indent=2, sort_keys=True)
    if args.out is None:
        emit(rendered)
        return EXIT_ACKNOWLEDGED
    args.out.write_text(rendered + "\n")
    emit(f"wrote {args.out}")
    return EXIT_ACKNOWLEDGED


COMMANDS = {"preview": preview, "run": run, "verify": verify, "adapt": adapt_command}


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    tokens = list(sys.argv[1:] if argv is None else argv)
    if tokens and tokens[0].startswith("--") and tokens[0] != "--help":
        tokens.insert(0, "preview")
    args = parser.parse_args(tokens)
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE
    try:
        return COMMANDS[args.command](args)
    except (IncidentError, UntrustedHost) as error:
        emit(f"error: {error}")
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())

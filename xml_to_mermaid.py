#!/usr/bin/env python3
"""
Convert a Rhapsody integration engine XML export to a Mermaid flowchart.

The diagram shows routes (processing pipelines) connected to comm points
(external systems). Router comm points (rhapsody:router) that mediate
between routes are shown as intermediate nodes.

Usage:
    python3 xml_to_mermaid.py <input.xml> [output.md]
    python3 xml_to_mermaid.py <input.xml> --area "6. ePharmacy v8"
    python3 xml_to_mermaid.py <input.xml> --subgraphs
    python3 xml_to_mermaid.py <input.xml> --include-sinks
    python3 xml_to_mermaid.py <input.xml> --broadcast-channels
    python3 xml_to_mermaid.py <input.xml> areas.txt --list-areas
    
 ---
  Arguments

  input_xml (required)

  The Rhapsody XML export file to parse.
  python3 xml_to_mermaid.py test.xml

  ---
  output (optional positional)

  Path to write the result as a .md file containing a fenced ```mermaid block. If omitted, output goes to stdout.
  python3 xml_to_mermaid.py test.xml diagram.md
  Must come immediately after the XML file, before any flags:
  python3 xml_to_mermaid.py test.xml diagram.md --area "2. Local"
  python3 xml_to_mermaid.py test.xml --config-detail
  python3 xml_to_mermaid.py test.xml --area "1. Admin" --config-detail
  ---
  --area AREA

  Filter the diagram to only routes in one folder area (the second segment of Rhapsody's folder path). Without this the full diagram has all 80 routes which is very large.
  python3 xml_to_mermaid.py test.xml --area "6. ePharmacy v8"
  The match is case-insensitive and prefix-based, so --area "6." would also match. To see all available areas:
  python3 -c "
  import xml.etree.ElementTree as ET
  root = ET.parse('test.xml').getroot()
  ns = 'urn:www.yourcompany.com/Rhapsody/Schema.xml'
  areas = sorted({
      el.text.split(';')[1].strip()
      for el in root.iter(f'{{{ns}}}Folder')
      if el.text and len(el.text.split(';')) >= 2
  })
  for a in areas: print(a)
  "

  ---
  --subgraphs

  Groups route nodes into labelled boxes by area. Comm point nodes sit outside the boxes but edges still cross into them. Most useful when generating the full diagram (no --area) so you
  can see which routes belong to which integration area.
  python3 xml_to_mermaid.py test.xml diagram.md --subgraphs
  Can be combined with --area — though with a single area filtered the box just wraps all visible routes.

  ---
  --include-sinks

  Sinks are Rhapsody's message-discard endpoints — they consume messages and do nothing with them (used for testing or suppressing unwanted output). They are hidden by default since they
  don't represent real external connections. Add this flag to show them as grey rectangles.
  python3 xml_to_mermaid.py test.xml --include-sinks
  In test.xml there are 46 Sink comm points so this will noticeably grow the diagram.

  ---
  Node colours (legend)

  ┌───────────────────────────────────────┬──────────┬──────────────────────────────────────────────────────────┐
  │                Colour                 │  Shape   │                         Meaning                          │
  ├───────────────────────────────────────┼──────────┼──────────────────────────────────────────────────────────┤
  │ Green parallelogram                   │ [/text/] │ Input comm point — external system pushing data in       │
  ├───────────────────────────────────────┼──────────┼──────────────────────────────────────────────────────────┤
  │ Green parallelogram + [bidirectional] │ [/text/] │ Comm point that both sends and receives (e.g. MLLP ACK)  │
  ├───────────────────────────────────────┼──────────┼──────────────────────────────────────────────────────────┤
  │ Blue rectangle                        │ [text]   │ Output comm point — external system receiving data       │
  ├───────────────────────────────────────┼──────────┼──────────────────────────────────────────────────────────┤
  │ Yellow rounded rectangle              │ (text)   │ Route (processing pipeline)                              │
  ├───────────────────────────────────────┼──────────┼──────────────────────────────────────────────────────────┤
  │ Red hexagon                           │ {text}   │ Static router — always dispatches to a fixed destination │
  ├───────────────────────────────────────┼──────────┼──────────────────────────────────────────────────────────┤
  │ Purple hexagon                        │ {text}   │ Dynamic router — destination set at runtime per message  │
  ├───────────────────────────────────────┼──────────┼──────────────────────────────────────────────────────────┤
  │ Grey rectangle                        │ [text]   │ Sink (only visible with --include-sinks)                 │
  └───────────────────────────────────────┴──────────┴──────────────────────────────────────────────────────────┘    
            
    
"""


import re
import sys
import xml.etree.ElementTree as ET
from argparse import ArgumentParser
from dataclasses import dataclass, field

NS = "urn:www.yourcompany.com/Rhapsody/Schema.xml"

EXTERNAL_TYPES = {
    "Database", "DatabaseInserter", "Directory", "E-mail", "FTPClient",
    "FTPServer", "HTTPClient", "HTTPServer", "JMSMessageConsumer",
    "JMSMessageProducer", "LLP", "SOAPWebServiceConsumer",
    "SOAPWebServiceProvider", "TCPClient", "TCPServer", "TimerCommPoint",
    "rhapsody:FileTransfer",
}


def _t(local: str) -> str:
    return f"{{{NS}}}{local}"


def _name_from_folder(folder: str) -> str:
    parts = [p.strip() for p in folder.split(";")]
    last = parts[-1].lower()
    if last in ("communication point", "communication points", "route", "routes"):
        return parts[-2] if len(parts) >= 2 else parts[-1]
    return parts[-1]


def _area_from_folder(folder: str) -> str:
    parts = [p.strip() for p in folder.split(";")]
    return parts[1] if len(parts) >= 2 else parts[0]


def _node_id(uid: str) -> str:
    return "n" + re.sub(r"[^A-Za-z0-9]", "_", uid)


def _channel_node_id(channel_name: str) -> str:
    return "ch_" + re.sub(r"[^A-Za-z0-9]", "_", channel_name)


def _label(text: str) -> str:
    return text.replace('"', "'")


_DETAIL_PROPS: dict[str, list[str]] = {
    "Directory":               ["INPUT_DIRECTORY_NAME", "OUTPUT_DIRECTORY_NAME"],
    "TCPClient":               ["HOST", "PORT"],
    "TCPServer":               ["LOCALPORT"],
    "Database":                ["Host", "DatabaseName"],
    "DatabaseInserter":        ["Host", "DatabaseName"],
    "E-mail":                  ["TO", "OUTGOING_HOST"],
    "HTTPClient":              ["URL"],
    "HTTPServer":              ["ContextPath", "LocalPort"],
    "rhapsody:FileTransfer":   ["Server", "Port"],
    "TimerCommPoint":          ["RefreshRate"],
    "SOAPWebServiceConsumer":  ["URL"],
    "LLP":                     ["HOST", "PORT"],
    "JMSMessageConsumer":      ["providerURL"],
    "JMSMessageProducer":      ["providerURL"],
}


def _format_detail(
    cp_type: str,
    config: dict[str, str],
    is_source: bool,
    variables: dict[str, str] | None = None,
) -> str:
    props = _DETAIL_PROPS.get(cp_type, [])
    if not props:
        return ""

    def resolve(v: str) -> str:
        return _resolve(v, variables) if variables else v

    if cp_type == "Directory":
        key = "INPUT_DIRECTORY_NAME" if is_source else "OUTPUT_DIRECTORY_NAME"
        val = config.get(key, "")
        if not val:
            val = config.get("INPUT_DIRECTORY_NAME") or config.get("OUTPUT_DIRECTORY_NAME", "")
        return resolve(val)

    if cp_type in ("TCPClient", "LLP"):
        host = resolve(config.get("HOST", ""))
        port = resolve(config.get("PORT", ""))
        if host or port:
            return f"{host}:{port}" if host else f":{port}"
        return ""

    if cp_type == "TCPServer":
        port = resolve(config.get("LOCALPORT", ""))
        return f":{port}" if port else ""

    if cp_type in ("Database", "DatabaseInserter"):
        host = resolve(config.get("Host", ""))
        db = resolve(config.get("DatabaseName", ""))
        parts = [p for p in [host, db] if p]
        return "/".join(parts)

    if cp_type == "TimerCommPoint":
        ms = config.get("RefreshRate", "")
        try:
            secs = int(ms) // 1000
            return f"every {secs}s"
        except (ValueError, TypeError):
            return ms

    if cp_type == "HTTPServer":
        path = resolve(config.get("ContextPath", ""))
        port = resolve(config.get("LocalPort", ""))
        if port and path:
            return f":{port}{path}"
        return port or path

    if cp_type == "rhapsody:FileTransfer":
        server = resolve(config.get("Server", ""))
        port = resolve(config.get("Port", ""))
        return f"{server}:{port}" if server else ""

    for key in props:
        val = config.get(key, "")
        if val:
            return resolve(val)
    return ""


@dataclass(slots=True)
class CPInfo:
    id: str
    name: str
    cp_type: str
    mode: str
    folder: str
    is_router: bool = False
    delivery_mode: str | None = None
    target_name: str = ""
    config: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RouteInfo:
    id: str
    name: str
    folder: str
    input_cp_ids: list[str] = field(default_factory=list)
    output_cp_ids: list[str] = field(default_factory=list)


def _resolve(value: str, variables: dict[str, str]) -> str:
    return re.sub(
        r"\$\(([^)]+)\)",
        lambda m: variables.get(m.group(1), m.group(0)),
        value,
    )


def parse_xml(filepath: str) -> tuple[dict[str, CPInfo], dict[str, RouteInfo], dict[str, str]]:
    tree = ET.parse(filepath)
    root = tree.getroot()

    cps: dict[str, CPInfo] = {}
    for el in root.iter(_t("CommPoint")):
        cp_id = el.find(_t("ID")).text.strip()
        cp_type = el.find(_t("Type")).text.strip()
        mode_el = el.find(_t("Mode"))
        mode = mode_el.text.strip() if mode_el is not None else ""
        folder_el = el.find(_t("Folder"))
        folder = folder_el.text.strip() if folder_el is not None else ""

        is_router = cp_type == "rhapsody:router"
        delivery_mode: str | None = None
        target_name = ""
        config: dict[str, str] = {}
        for prop in el.findall(f".//{_t('Configuration')}/{_t('Property')}"):
            name_el = prop.find(_t("Name"))
            val_el = prop.find(_t("Value"))
            if name_el is None or val_el is None or not val_el.text:
                continue
            val = val_el.text.strip()
            if not val:
                continue
            config[name_el.text] = val
            if is_router:
                if name_el.text == "DeliveryMode":
                    delivery_mode = val
                elif name_el.text == "TargetName":
                    target_name = val

        cps[cp_id] = CPInfo(
            id=cp_id,
            name=_name_from_folder(folder) if folder else cp_id[:8],
            cp_type=cp_type,
            mode=mode,
            folder=folder,
            is_router=is_router,
            delivery_mode=delivery_mode,
            target_name=target_name,
            config=config,
        )

    routes: dict[str, RouteInfo] = {}
    for el in root.iter(_t("Route")):
        route_id = el.find(_t("ID")).text.strip()
        folder_el = el.find(_t("Folder"))
        folder = folder_el.text.strip() if folder_el is not None else ""

        input_cps = [
            icp.find(_t("ID")).text.strip()
            for icp in el.findall(f".//{_t('InputCommPoints')}/{_t('InputCommPoint')}")
        ]
        output_cps = [
            id_el.text.strip()
            for id_el in el.findall(f".//{_t('OutputCommPoints')}/{_t('ID')}")
        ]

        routes[route_id] = RouteInfo(
            id=route_id,
            name=_name_from_folder(folder) if folder else route_id[:8],
            folder=folder,
            input_cp_ids=input_cps,
            output_cp_ids=output_cps,
        )

    # Augment route connections from CommPoint back-references.
    # The Route XML only stores explicit InputCommPoints/OutputCommPoints, but the
    # CommPoint XML stores the mirror: OutputRoutes (routes this CP feeds into) and
    # InputRoutes (routes that send to this CP). Many routes omit their InputCommPoints
    # and rely solely on these back-references, so we must read both directions.
    for el in root.iter(_t("CommPoint")):
        cp_id_el = el.find(_t("ID"))
        if cp_id_el is None or not cp_id_el.text:
            continue
        cp_id = cp_id_el.text.strip()
        if cp_id not in cps:
            continue
        cp_mode = cps[cp_id].mode if cp_id in cps else ""
        for rid_el in el.findall(f".//{_t('OutputRoutes')}/{_t('ID')}"):
            if rid_el.text:
                rid = rid_el.text.strip()
                # cpmOutput CPs can only receive from routes, never feed into them.
                if rid in routes and cp_id not in routes[rid].input_cp_ids and cp_mode != "cpmOutput":
                    routes[rid].input_cp_ids.append(cp_id)
        for rid_el in el.findall(f".//{_t('InputRoutes')}/{_t('ID')}"):
            if rid_el.text:
                rid = rid_el.text.strip()
                # cpmInput CPs can only feed into routes, never receive from them.
                if rid in routes and cp_id not in routes[rid].output_cp_ids and cp_mode != "cpmInput":
                    routes[rid].output_cp_ids.append(cp_id)

    variables: dict[str, str] = {}
    vars_el = root.find(_t("Variables"))
    if vars_el is not None:
        for var in vars_el.findall(_t("Variable")):
            name_el = var.find(_t("Name"))
            val_el = var.find(_t("Value"))
            if name_el is not None and name_el.text:
                variables[name_el.text] = (
                    val_el.text.strip() if val_el is not None and val_el.text else ""
                )

    return cps, routes, variables


def _cp_node_def(
    cp: CPInfo,
    is_source: bool,
    is_dest: bool,
    show_detail: bool = False,
    variables: dict[str, str] | None = None,
) -> tuple[str, str]:
    nid = _node_id(cp.id)
    lbl = _label(cp.name)
    short_type = cp.cp_type.replace("rhapsody:", "")

    if cp.is_router:
        mode_str = "Dynamic" if cp.delivery_mode == "dynamicDestination" else "Static"
        css = "dynamicRouter" if cp.delivery_mode == "dynamicDestination" else "staticRouter"
        return f'    {nid}{{"{lbl}\\n[{mode_str} Router]"}}', css

    if cp.cp_type == "Sink":
        return f'    {nid}["{lbl}\\n[Sink]"]', "sink"

    detail = ""
    if show_detail:
        raw = _format_detail(cp.cp_type, cp.config, is_source, variables)
        if raw:
            detail = f"\\n{_label(raw)}"

    if is_source and not is_dest:
        return f'    {nid}[/"{lbl}\\n({short_type}){detail}"/]', "inputCP"
    if is_dest and not is_source:
        return f'    {nid}["{lbl}\\n({short_type}){detail}"]', "outputCP"
    return f'    {nid}[/"{lbl}\\n({short_type}){detail}\\n[bidirectional]"/]', "inputCP"


def _resolved_target_name(cp: CPInfo, variables: dict[str, str] | None) -> str:
    """Return the resolved TargetName for a router CP, or '' if unresolvable at parse time."""
    if not cp.target_name:
        return ""
    resolved = _resolve(cp.target_name, variables or {})
    # Runtime message property lookups (prefix @) cannot be statically resolved.
    if resolved.startswith("@"):
        return ""
    return resolved


def generate_mermaid(
    cps: dict[str, CPInfo],
    routes: dict[str, RouteInfo],
    variables: dict[str, str] | None = None,
    area_filter: str | None = None,
    include_sinks: bool = False,
    use_subgraphs: bool = False,
    config_detail: bool = False,
    show_broadcast_channels: bool = False,
) -> str:
    lines: list[str] = ["flowchart LR"]
    lines += [
        "    classDef inputCP         fill:#d4edda,stroke:#28a745,color:#000",
        "    classDef outputCP        fill:#cce5ff,stroke:#004085,color:#000",
        "    classDef route           fill:#fff3cd,stroke:#856404,color:#000",
        "    classDef staticRouter    fill:#f8d7da,stroke:#721c24,color:#000",
        "    classDef dynamicRouter   fill:#e2d9f3,stroke:#4a235a,color:#000",
        "    classDef sink            fill:#e2e3e5,stroke:#6c757d,color:#666",
        "    classDef broadcastChannel fill:#fff8e1,stroke:#f9a825,color:#000",
        "    classDef unknownSource   fill:#f5f5f5,stroke:#9e9e9e,stroke-dasharray:5 5,color:#999",
    ]

    declared_cps: dict[str, str] = {}    # cp_id  -> node_id (or channel_node_id)
    declared_routes: dict[str, str] = {} # route_id -> node_id
    declared_channels: dict[str, str] = {} # channel_name -> node_id
    cp_node_defs: list[str] = []
    route_node_defs: dict[str, list[str]] = {}
    edges: list[str] = []
    edges_seen: set[str] = set()
    class_assigns: list[str] = []
    routes_with_input_edges: set[str] = set()

    area_routes: dict[str, list[RouteInfo]] = {}
    for route in routes.values():
        if area_filter and not _area_from_folder(route.folder).lower().startswith(
            area_filter.lower()
        ):
            continue
        area = _area_from_folder(route.folder)
        area_routes.setdefault(area, []).append(route)

    source_cp_ids: set[str] = set()
    dest_cp_ids: set[str] = set()
    for route_list in area_routes.values():
        for route in route_list:
            source_cp_ids.update(route.input_cp_ids)
            dest_cp_ids.update(route.output_cp_ids)

    def add_edge(edge: str) -> None:
        if edge not in edges_seen:
            edges_seen.add(edge)
            edges.append(edge)

    def add_broadcast_channel(channel_name: str) -> str:
        if channel_name in declared_channels:
            return declared_channels[channel_name]
        nid = _channel_node_id(channel_name)
        declared_channels[channel_name] = nid
        cp_node_defs.append(f'    {nid}(("{_label(channel_name)}\\n[Broadcast]"))')
        class_assigns.append(f"    {nid}:::broadcastChannel")
        return nid

    def add_cp(cp: CPInfo) -> str:
        if cp.id in declared_cps:
            return declared_cps[cp.id]

        # Router CPs with a resolvable TargetName are broadcast publishers.
        # Collapse all publishers for the same channel into one shared channel node.
        if show_broadcast_channels and cp.is_router:
            channel = _resolved_target_name(cp, variables)
            if channel:
                nid = add_broadcast_channel(channel)
                declared_cps[cp.id] = nid
                return nid

        nid = _node_id(cp.id)
        declared_cps[cp.id] = nid
        defn, css = _cp_node_def(
            cp,
            is_source=cp.id in source_cp_ids,
            is_dest=cp.id in dest_cp_ids,
            show_detail=config_detail,
            variables=variables,
        )
        cp_node_defs.append(defn)
        class_assigns.append(f"    {nid}:::{css}")
        return nid

    def add_route(route: RouteInfo, area: str) -> str:
        if route.id in declared_routes:
            return declared_routes[route.id]
        nid = _node_id(route.id)
        declared_routes[route.id] = nid
        lbl = _label(route.name)
        route_node_defs.setdefault(area, []).append(f'    {nid}("{lbl}")')
        class_assigns.append(f"    {nid}:::route")
        return nid

    def process_route(route: RouteInfo, area: str) -> None:
        r_nid = add_route(route, area)

        # Track which CP node IDs already have an inbound edge to this route.
        # Used below to suppress the reverse edge and prevent cp→route→cp cycles.
        cp_nids_as_inputs: set[str] = set()

        for cp_id in route.input_cp_ids:
            cp = cps.get(cp_id)
            if not cp:
                continue
            if not include_sinks and cp.cp_type == "Sink":
                continue
            cp_nid = add_cp(cp)
            add_edge(f"    {cp_nid} --> {r_nid}")
            cp_nids_as_inputs.add(cp_nid)
            routes_with_input_edges.add(route.id)

        for cp_id in route.output_cp_ids:
            cp = cps.get(cp_id)
            if not cp:
                continue
            if not include_sinks and cp.cp_type == "Sink":
                continue
            cp_nid = add_cp(cp)
            if cp_nid in cp_nids_as_inputs:
                continue  # already connected as input; skip reverse edge
            add_edge(f"    {r_nid} --> {cp_nid}")

    if not area_routes and area_filter:
        print(
            f"Warning: --area {area_filter!r} matched no routes. "
            "Run with --list-areas to see valid values.",
            file=sys.stderr,
        )

    for area, route_list in sorted(area_routes.items()):
        for route in route_list:
            process_route(route, area)

    # Routes that received no input edges have sources that can only be determined
    # at runtime (filter scripts, dynamic destination routing). Mark them visually.
    floater_route_ids = [
        rid for rid in declared_routes if rid not in routes_with_input_edges
    ]
    if floater_route_ids:
        u_nid = "unknown_source"
        cp_node_defs.append('    unknown_source["?\\n[source unknown]"]')
        class_assigns.append("    unknown_source:::unknownSource")
        for rid in floater_route_ids:
            add_edge(f"    {u_nid} -.-> {declared_routes[rid]}")

    lines += cp_node_defs
    if use_subgraphs:
        for area, r_defs in sorted(route_node_defs.items()):
            safe_area = re.sub(r"[^A-Za-z0-9]", "_", area)
            lines.append(f'    subgraph {safe_area} ["{_label(area)}"]')
            lines += r_defs
            lines.append("    end")
    else:
        for r_defs in route_node_defs.values():
            lines += r_defs

    lines += edges
    lines += class_assigns
    return "\n".join(lines)


def main() -> None:
    parser = ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("input_xml", help="Rhapsody XML export file")
    parser.add_argument(
        "output", nargs="?", help="Output .md file (default: stdout)"
    )
    parser.add_argument(
        "--area",
        metavar="AREA",
        help='Filter to a folder area, e.g. "6. ePharmacy v8"',
    )
    parser.add_argument(
        "--subgraphs",
        action="store_true",
        help="Group nodes into Mermaid subgraphs by folder area",
    )
    parser.add_argument(
        "--include-sinks",
        action="store_true",
        help="Include Sink comm points (message-discard endpoints) in diagram",
    )
    parser.add_argument(
        "--config-detail",
        action="store_true",
        help="Append key config properties to comm point labels (e.g. host:port, directory path)",
    )
    parser.add_argument(
        "--broadcast-channels",
        action="store_true",
        help=(
            "Collapse router CPs that share a TargetName into a single named broadcast "
            "channel node, showing the fan-in pattern for each channel"
        ),
    )
    parser.add_argument(
        "--list-areas",
        action="store_true",
        help="List valid --area values from the XML and exit",
    )
    args = parser.parse_args()

    print(f"Parsing {args.input_xml} ...", file=sys.stderr)
    cps, routes, variables = parse_xml(args.input_xml)
    print(
        f"Found {len(cps)} comm points, {len(routes)} routes, "
        f"{len(variables)} variables",
        file=sys.stderr,
    )

    if args.list_areas:
        areas = sorted({_area_from_folder(r.folder) for r in routes.values()})
        if args.output:
            with open(args.output, "w") as fh:
                fh.write("\n".join(areas) + "\n")
            print(f"Written to {args.output}", file=sys.stderr)
        else:
            for area in areas:
                print(area)
        return

    diagram = generate_mermaid(
        cps,
        routes,
        variables=variables,
        area_filter=args.area,
        include_sinks=args.include_sinks,
        use_subgraphs=args.subgraphs,
        config_detail=args.config_detail,
        show_broadcast_channels=args.broadcast_channels,
    )

    if args.output:
        with open(args.output, "w") as fh:
            fh.write("```mermaid\n")
            fh.write(diagram)
            fh.write("\n```\n")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print("```mermaid")
        print(diagram)
        print("```")


if __name__ == "__main__":
    main()
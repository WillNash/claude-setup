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
from typing import Optional

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


def _label(text: str) -> str:
    return text.replace('"', "'")


# Config properties to extract per comm point type, in priority order.
# The first non-empty value found is used as the detail label.
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


def _format_detail(cp_type: str, config: dict[str, str], is_source: bool) -> str:
    """Return a short detail string for a comm point label, or empty string."""
    props = _DETAIL_PROPS.get(cp_type, [])
    if not props:
        return ""

    if cp_type == "Directory":
        key = "INPUT_DIRECTORY_NAME" if is_source else "OUTPUT_DIRECTORY_NAME"
        val = config.get(key, "")
        if not val:
            val = config.get("INPUT_DIRECTORY_NAME") or config.get("OUTPUT_DIRECTORY_NAME", "")
        return val

    if cp_type in ("TCPClient", "LLP"):
        host = config.get("HOST", "")
        port = config.get("PORT", "")
        if host or port:
            return f"{host}:{port}" if host else f":{port}"

    if cp_type == "TCPServer":
        port = config.get("LOCALPORT", "")
        return f":{port}" if port else ""

    if cp_type in ("Database", "DatabaseInserter"):
        host = config.get("Host", "")
        db = config.get("DatabaseName", "")
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
        path = config.get("ContextPath", "")
        port = config.get("LocalPort", "")
        if port and path:
            return f":{port}{path}"
        return port or path

    if cp_type == "rhapsody:FileTransfer":
        server = config.get("Server", "")
        port = config.get("Port", "")
        return f"{server}:{port}" if server else ""

    # Default: return first non-empty value from the priority list
    for key in props:
        val = config.get(key, "")
        if val:
            return val
    return ""


@dataclass
class CPInfo:
    id: str
    name: str
    cp_type: str
    mode: str
    folder: str
    is_router: bool = False
    delivery_mode: Optional[str] = None  # None | "alwaysStatic" | "dynamicDestination"
    config: dict = field(default_factory=dict)


@dataclass
class RouteInfo:
    id: str
    name: str
    folder: str
    input_cp_ids: list = field(default_factory=list)
    output_cp_ids: list = field(default_factory=list)


def parse_xml(filepath: str) -> tuple[dict, dict]:
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
        delivery_mode = None
        config: dict[str, str] = {}
        for prop in el.findall(f".//{_t('Configuration')}/{_t('Property')}"):
            name_el = prop.find(_t("Name"))
            val_el = prop.find(_t("Value"))
            if name_el is not None and val_el is not None and val_el.text:
                val = val_el.text.strip()
                if val:
                    config[name_el.text] = val
                if is_router and name_el.text == "DeliveryMode":
                    delivery_mode = val_el.text

        cps[cp_id] = CPInfo(
            id=cp_id,
            name=_name_from_folder(folder) if folder else cp_id[:8],
            cp_type=cp_type,
            mode=mode,
            folder=folder,
            is_router=is_router,
            delivery_mode=delivery_mode,
            config=config,
        )

    routes: dict[str, RouteInfo] = {}
    for el in root.iter(_t("Route")):
        route_id = el.find(_t("ID")).text.strip()
        folder_el = el.find(_t("Folder"))
        folder = folder_el.text.strip() if folder_el is not None else ""

        input_cps = [
            icp.find(_t("ID")).text.strip()
            for icp in el.findall(
                f".//{_t('InputCommPoints')}/{_t('InputCommPoint')}"
            )
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

    return cps, routes


def _cp_node_def(
    cp: CPInfo, is_source: bool, is_dest: bool, show_detail: bool = False
) -> tuple[str, str]:
    """Return (node definition line, css class name) for a comm point."""
    nid = _node_id(cp.id)
    lbl = _label(cp.name)
    short_type = cp.cp_type.replace("rhapsody:", "")

    if cp.is_router:
        mode_str = "Dynamic" if cp.delivery_mode == "dynamicDestination" else "Static"
        return f'    {nid}{{"{lbl}\\n[{mode_str} Router]"}}', (
            "dynamicRouter" if cp.delivery_mode == "dynamicDestination" else "staticRouter"
        )

    if cp.cp_type == "Sink":
        return f'    {nid}["{lbl}\\n[Sink]"]', "sink"

    detail = ""
    if show_detail:
        raw = _format_detail(cp.cp_type, cp.config, is_source)
        if raw:
            detail = f"\\n{_label(raw)}"

    # Determine direction from actual usage in routes
    if is_source and not is_dest:
        return f'    {nid}[/"{lbl}\\n({short_type}){detail}"/]', "inputCP"
    if is_dest and not is_source:
        return f'    {nid}["{lbl}\\n({short_type}){detail}"]', "outputCP"
    # Bidirectional — appears as both input and output
    return f'    {nid}[/"{lbl}\\n({short_type}){detail}\\n[bidirectional]"/]', "inputCP"


def generate_mermaid(
    cps: dict[str, CPInfo],
    routes: dict[str, RouteInfo],
    area_filter: Optional[str] = None,
    include_sinks: bool = False,
    use_subgraphs: bool = False,
    config_detail: bool = False,
) -> str:
    lines: list[str] = ["flowchart LR"]
    lines += [
        "    classDef inputCP  fill:#d4edda,stroke:#28a745,color:#000",
        "    classDef outputCP fill:#cce5ff,stroke:#004085,color:#000",
        "    classDef route    fill:#fff3cd,stroke:#856404,color:#000",
        "    classDef staticRouter  fill:#f8d7da,stroke:#721c24,color:#000",
        "    classDef dynamicRouter fill:#e2d9f3,stroke:#4a235a,color:#000",
        "    classDef sink     fill:#e2e3e5,stroke:#6c757d,color:#666",
    ]

    declared_cps: dict[str, str] = {}   # cp_id  -> node_id
    declared_routes: dict[str, str] = {}  # route_id -> node_id
    node_defs: list[str] = []
    edges: list[str] = []
    class_assigns: list[str] = []

    # Group routes by area when subgraphs requested
    area_routes: dict[str, list[RouteInfo]] = {}
    for route in routes.values():
        if area_filter:
            if not _area_from_folder(route.folder).lower().startswith(
                area_filter.lower()
            ):
                continue
        area = _area_from_folder(route.folder)
        area_routes.setdefault(area, []).append(route)

    # Pre-compute which CPs are sources (feed routes) vs destinations (receive from routes)
    source_cp_ids: set[str] = set()
    dest_cp_ids: set[str] = set()
    for route_list in area_routes.values():
        for route in route_list:
            source_cp_ids.update(route.input_cp_ids)
            dest_cp_ids.update(route.output_cp_ids)

    def add_cp(cp: CPInfo) -> str:
        if cp.id in declared_cps:
            return declared_cps[cp.id]
        nid = _node_id(cp.id)
        declared_cps[cp.id] = nid
        defn, css = _cp_node_def(
            cp,
            is_source=cp.id in source_cp_ids,
            is_dest=cp.id in dest_cp_ids,
        )
        node_defs.append(defn)
        class_assigns.append(f"    {nid}:::{css}")
        return nid

    # route node defs grouped by area (for subgraphs); CP nodes always go top-level
    cp_node_defs: list[str] = []   # comm point node definitions
    route_node_defs: dict[str, list[str]] = {}  # area -> route node definitions

    def add_route(route: RouteInfo, area: str) -> str:
        if route.id in declared_routes:
            return declared_routes[route.id]
        nid = _node_id(route.id)
        declared_routes[route.id] = nid
        lbl = _label(route.name)
        route_node_defs.setdefault(area, []).append(f'    {nid}("{lbl}")')
        class_assigns.append(f"    {nid}:::route")
        return nid

    # Override add_cp to write to cp_node_defs
    def add_cp(cp: CPInfo) -> str:
        if cp.id in declared_cps:
            return declared_cps[cp.id]
        nid = _node_id(cp.id)
        declared_cps[cp.id] = nid
        defn, css = _cp_node_def(
            cp,
            is_source=cp.id in source_cp_ids,
            is_dest=cp.id in dest_cp_ids,
            show_detail=config_detail,
        )
        cp_node_defs.append(defn)
        class_assigns.append(f"    {nid}:::{css}")
        return nid

    def process_route(route: RouteInfo, area: str) -> None:
        r_nid = add_route(route, area)

        for cp_id in route.input_cp_ids:
            cp = cps.get(cp_id)
            if not cp:
                continue
            if not include_sinks and cp.cp_type == "Sink":
                continue
            cp_nid = add_cp(cp)
            edges.append(f"    {cp_nid} --> {r_nid}")

        for cp_id in route.output_cp_ids:
            cp = cps.get(cp_id)
            if not cp:
                continue
            if not include_sinks and cp.cp_type == "Sink":
                continue
            cp_nid = add_cp(cp)
            edges.append(f"    {r_nid} --> {cp_nid}")

    for area, route_list in sorted(area_routes.items()):
        for route in route_list:
            process_route(route, area)

    # Build output: CP nodes first (top-level), then routes in subgraphs or flat
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
    args = parser.parse_args()

    print(f"Parsing {args.input_xml} ...", file=sys.stderr)
    cps, routes = parse_xml(args.input_xml)
    print(
        f"Found {len(cps)} comm points, {len(routes)} routes", file=sys.stderr
    )

    diagram = generate_mermaid(
        cps,
        routes,
        area_filter=args.area,
        include_sinks=args.include_sinks,
        use_subgraphs=args.subgraphs,
        config_detail=args.config_detail,
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

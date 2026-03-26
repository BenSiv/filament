import argparse
import json
import os
import sqlite3


def _fetch_lead_id(cur, lead_nid, source_ref):
    if lead_nid:
        return lead_nid
    if not source_ref:
        return None
    cur.execute(
        "SELECT nid FROM ai_note WHERE source_type = 'lead' AND source_ref = ? LIMIT 1",
        (source_ref,),
    )
    row = cur.fetchone()
    return row[0] if row else None


def _build_graph(cur, lead_nid):
    cur.execute(
        """
        SELECT nid, title, source_type, source_ref, tier, process_level
        FROM ai_note
        WHERE nid = ?
        """,
        (lead_nid,),
    )
    lead_row = cur.fetchone()
    if not lead_row:
        return None

    nodes = []
    edges = []

    def add_node(row):
        nid, title, source_type, source_ref, tier, process_level = row
        nodes.append(
            {
                "nid": nid,
                "title": title,
                "source_type": source_type,
                "source_ref": source_ref,
                "tier": tier,
                "process_level": process_level,
            }
        )

    add_node(lead_row)

    cur.execute(
        """
        SELECT from_nid, to_nid, link_type, weight
        FROM ai_note_link
        WHERE from_nid = ?
        """,
        (lead_nid,),
    )
    link_rows = cur.fetchall()
    related_ids = [row[1] for row in link_rows]

    if related_ids:
        cur.execute(
            f"""
            SELECT nid, title, source_type, source_ref, tier, process_level
            FROM ai_note
            WHERE nid IN ({','.join('?' for _ in related_ids)})
            """,
            related_ids,
        )
        for row in cur.fetchall():
            add_node(row)

    for from_nid, to_nid, link_type, weight in link_rows:
        edges.append(
            {
                "from": from_nid,
                "to": to_nid,
                "type": link_type,
                "weight": weight,
            }
        )

    return {"nodes": nodes, "edges": edges}


def _to_dot(graph):
    lines = ["digraph EvidenceGraph {"]
    for node in graph["nodes"]:
        label = f"{node['nid']}: {node['source_type']}"
        lines.append(f"  {node['nid']} [label=\"{label}\"]; ")
    for edge in graph["edges"]:
        label = edge.get("type", "")
        lines.append(f"  {edge['from']} -> {edge['to']} [label=\"{label}\"]; ")
    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export evidence graph for a lead")
    parser.add_argument("--db", default="data/knowledge.fossil", help="Path to Fossil DB")
    parser.add_argument("--lead-nid", type=int, default=0, help="Lead note id")
    parser.add_argument("--source-ref", default="", help="Lead source_ref")
    parser.add_argument("--format", default="json", choices=["json", "dot"], help="Output format")
    parser.add_argument("--out", default="", help="Output file path (optional)")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Fossil DB not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    lead_nid = _fetch_lead_id(cur, args.lead_nid or None, args.source_ref)
    if not lead_nid:
        print("Lead note not found. Provide --lead-nid or --source-ref.")
        conn.close()
        return

    graph = _build_graph(cur, lead_nid)
    conn.close()

    if not graph:
        print("No graph available for lead.")
        return

    if args.format == "dot":
        output = _to_dot(graph)
    else:
        output = json.dumps(graph, indent=2)

    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
        print(f"Wrote graph to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()

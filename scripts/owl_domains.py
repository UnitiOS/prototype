"""owl_domains — give a gen-owl TTL the explicit domains it does not write.

`gen-owl` states where a property may be used the OWL way: a class carries an
`owl:Restriction` on the property, and the property itself gets no
`rdfs:domain`. That is correct and it is unreadable. A node-link viewer draws a
property as an edge only when it can see both ends, so with no domain every
relationship in the map hangs off one generic node.

This walks the restrictions and writes the missing end back onto the property.

**Two domains are an intersection, not a union.** `p rdfs:domain A` and
`p rdfs:domain B` together say that anything carrying `p` is both an A and a B
— which is false here and would be a file that looks right and is wrong. So:

    used by one class     rdfs:domain that class
    used by more          rdfs:domain [ owl:unionOf ( ... ) ]

Ranges are read the same way, from `owl:allValuesFrom`, but only for a property
that has no `rdfs:range` already — gen-owl does write those.

The output is a **view**. It is derived, it belongs under `build/`, and nothing
under `components/` ever reads it back.

    owl_domains.py in.ttl --out out.ttl
"""

import argparse
import sys
from collections import defaultdict

from rdflib import BNode, Graph, RDF, RDFS
from rdflib.collection import Collection
from rdflib.namespace import OWL

PROPERTY_TYPES = (OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty,
                  RDF.Property)


def restrictions(graph):
    """property -> {classes that restrict it}, property -> {values it may take}.

    Only a *named* class counts as a domain: a restriction hung off a blank
    node is part of some larger expression and naming it says nothing.
    """
    domains = defaultdict(set)
    ranges = defaultdict(set)
    for klass, _, node in graph.triples((None, RDFS.subClassOf, None)):
        if (node, RDF.type, OWL.Restriction) not in graph:
            continue
        prop = graph.value(node, OWL.onProperty)
        if prop is None:
            continue
        if not isinstance(klass, BNode):
            domains[prop].add(klass)
        for target in graph.objects(node, OWL.allValuesFrom):
            if not isinstance(target, BNode):
                ranges[prop].add(target)
    return domains, ranges


def union_of(graph, members):
    """A class expression for more than one member. One blank node, one list."""
    node, first = BNode(), BNode()
    graph.add((node, RDF.type, OWL.Class))
    Collection(graph, first, sorted(members))
    graph.add((node, OWL.unionOf, first))
    return node


def state(graph, prop, predicate, members):
    """Write one domain or range. Sorted, so two runs give the same file."""
    members = sorted(members)
    graph.add((prop, predicate, members[0] if len(members) == 1
               else union_of(graph, members)))


def process(graph):
    properties = {s for t in PROPERTY_TYPES for s in graph.subjects(RDF.type, t)}
    domains, ranges = restrictions(graph)

    counts = {"properties": len(properties), "domain_single": 0, "domain_union": 0,
              "domain_none": 0, "range_kept": 0, "range_added": 0, "range_none": 0}

    for prop in sorted(properties):
        found = domains.get(prop, set())
        if not found:
            counts["domain_none"] += 1
        else:
            state(graph, prop, RDFS.domain, found)
            counts["domain_single" if len(found) == 1 else "domain_union"] += 1

        if (prop, RDFS.range, None) in graph:
            counts["range_kept"] += 1
            continue
        found = ranges.get(prop, set())
        if not found:
            counts["range_none"] += 1
        else:
            state(graph, prop, RDFS.range, found)
            counts["range_added"] += 1

    return counts


def edges(graph):
    """Properties a node-link viewer can draw: both ends named, both classes."""
    drawable = 0
    for prop in set(graph.subjects(RDF.type, OWL.ObjectProperty)):
        has_domain = any(True for _ in graph.objects(prop, RDFS.domain))
        ends = [o for o in graph.objects(prop, RDFS.range)
                if (o, RDF.type, OWL.Class) in graph]
        if has_domain and ends:
            drawable += 1
    return drawable


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", help="a TTL written by gen-owl")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    graph = Graph()
    graph.parse(args.source, format="turtle")
    before = {"triples": len(graph),
              "domains": sum(1 for _ in graph.triples((None, RDFS.domain, None))),
              "ranges": sum(1 for _ in graph.triples((None, RDFS.range, None))),
              "drawable": edges(graph)}

    counts = process(graph)
    graph.serialize(destination=args.out, format="turtle")

    after = {"triples": len(graph),
             "domains": sum(1 for _ in graph.triples((None, RDFS.domain, None))),
             "ranges": sum(1 for _ in graph.triples((None, RDFS.range, None))),
             "drawable": edges(graph)}

    for label, value in [("properties", counts["properties"]),
                         ("domain, one class", counts["domain_single"]),
                         ("domain, union", counts["domain_union"]),
                         ("domain, none found", counts["domain_none"]),
                         ("range already written", counts["range_kept"]),
                         ("range added", counts["range_added"]),
                         ("range, none found", counts["range_none"])]:
        print(f"{label:24} {value}")
    for key in ("triples", "domains", "ranges", "drawable"):
        print(f"{key:24} {before[key]} -> {after[key]}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

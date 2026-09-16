from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

@dataclass
class StandardUriEntry:
    curie: str
    uri: str
    title: str
    description: str
    recommended_range: str
    archetype: str  # 'Resource' | 'Event' | 'Commitment' | 'Agent' | 'Any'
    domain: str     # 'inventory' | 'finance' | 'procurement' | 'common'

# Built-in Standard Universal Semantic URIs for Enterprise Foundations
BUILTIN_CATALOG: List[StandardUriEntry] = [
    # --- INVENTORY & LOGISTICS ---
    StandardUriEntry(
        curie='inv:quantity',
        uri='https://w3id.org/uniti/vocab/inv#quantity',
        title='Physical Quantity',
        description='Universal measurable count, weight, or volume of a physical resource.',
        recommended_range='decimal',
        archetype='Resource',
        domain='inventory',
    ),
    StandardUriEntry(
        curie='inv:source_location',
        uri='https://w3id.org/uniti/vocab/inv#source_location',
        title='Source Location',
        description='Origin physical or virtual site from which a resource is dispatched.',
        recommended_range='PhysicalLocation',
        archetype='Event',
        domain='inventory',
    ),
    StandardUriEntry(
        curie='inv:target_location',
        uri='https://w3id.org/uniti/vocab/inv#target_location',
        title='Target Location',
        description='Destination physical or virtual site where a resource is received.',
        recommended_range='PhysicalLocation',
        archetype='Event',
        domain='inventory',
    ),
    StandardUriEntry(
        curie='inv:batch_id',
        uri='https://w3id.org/uniti/vocab/inv#batch_id',
        title='Batch or Lot Number',
        description='Unique manufacturing batch, lot, or harvest tracking code.',
        recommended_range='string',
        archetype='Resource',
        domain='inventory',
    ),
    StandardUriEntry(
        curie='inv:unit_of_measure',
        uri='https://w3id.org/uniti/vocab/inv#unit_of_measure',
        title='Unit of Measure',
        description='Standard ISO or customary unit abbreviation (e.g. kg, m, l, pcs).',
        recommended_range='string',
        archetype='Resource',
        domain='inventory',
    ),

    # --- PROCUREMENT & CONTRACTS ---
    StandardUriEntry(
        curie='proc:po_number',
        uri='https://w3id.org/uniti/vocab/proc#po_number',
        title='Purchase Order Number',
        description='Official identifier of a bilateral purchase agreement.',
        recommended_range='string',
        archetype='Commitment',
        domain='procurement',
    ),
    StandardUriEntry(
        curie='proc:unit_price',
        uri='https://w3id.org/uniti/vocab/proc#unit_price',
        title='Agreed Unit Price',
        description='Price per single unit of resource stipulated in a commitment.',
        recommended_range='decimal',
        archetype='Commitment',
        domain='procurement',
    ),
    StandardUriEntry(
        curie='proc:vendor',
        uri='https://w3id.org/uniti/vocab/proc#vendor',
        title='Supplier / Vendor',
        description='The external supplying organization fulfilling the commitment.',
        recommended_range='Organization',
        archetype='Commitment',
        domain='procurement',
    ),

    # --- FINANCIAL & ACCOUNTING ---
    StandardUriEntry(
        curie='fin:amount',
        uri='https://w3id.org/uniti/vocab/fin#amount',
        title='Monetary Amount',
        description='Monetary value of an event or assertion in standard currency.',
        recommended_range='decimal',
        archetype='Event',
        domain='finance',
    ),
    StandardUriEntry(
        curie='fin:currency',
        uri='https://w3id.org/uniti/vocab/fin#currency',
        title='Currency Code',
        description='Three-letter ISO 4217 currency symbol (e.g. IDR, USD, EUR).',
        recommended_range='string',
        archetype='Event',
        domain='finance',
    ),
]

class SemanticCatalog:
    def __init__(self, entries: Optional[List[StandardUriEntry]] = None):
        self.entries = entries or BUILTIN_CATALOG

    def search(self, query: str, domain: Optional[str] = None, limit: int = 5) -> List[Dict]:
        q = query.lower().strip()
        matches = []
        for entry in self.entries:
            if domain and entry.domain.lower() != domain.lower():
                continue
            score = 0
            if q in entry.curie.lower():
                score += 10
            if q in entry.title.lower():
                score += 8
            if q in entry.description.lower():
                score += 5
            for word in q.split():
                if word in entry.description.lower() or word in entry.title.lower():
                    score += 2
            if score > 0:
                matches.append((score, asdict(entry)))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:limit]]

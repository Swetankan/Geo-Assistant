from collections import deque
import networkx as nx


class EvidenceGraph:
    def __init__(self,entities,relations,fan_out=20,max_nodes=200):
        if fan_out < 1 or max_nodes < 1:
            raise ValueError('Positive graph bounds required')
        self.entities = {e.id:e for e in entities}
        self.relations = {r.id:r for r in relations}
        self.graph = nx.MultiGraph()
        self.graph.add_nodes_from(self.entities)
        self.fan_out, self.max_nodes = fan_out,max_nodes
        for r in relations:
            if r.source_id not in self.entities or r.target_id not in self.entities:
                raise ValueError('Relation references unknown entity')
            self.graph.add_edge(r.source_id,r.target_id,key=r.id,relation=r)

    def neighbours(self,entity_id,hops,types=None):
        if hops not in (1,2):
            raise ValueError('Only one/two hops supported')
        if entity_id not in self.graph:
            return []
        seen, queue, results = {entity_id},deque([(entity_id,[],[entity_id])]),[]
        while queue and len(seen) < self.max_nodes:
            node,path,nodes = queue.popleft()
            if len(path) == hops:
                continue
            candidates = []
            for target,edges in self.graph[node].items():
                for edge in edges.values():
                    r = edge['relation']
                    if types is None or r.type in types:
                        candidates.append((target,r))
            expanded = 0
            for target,r in sorted(candidates,key=lambda x:(-x[1].weight,x[0],x[1].id)):
                if target in seen:
                    continue
                if expanded >= self.fan_out or len(seen) >= self.max_nodes:
                    break
                seen.add(target)
                expanded += 1
                record = dict(entity_id=target,edge_ids=path+[r.id],node_ids=nodes+[target])
                results.append(record)
                queue.append((target,record['edge_ids'],record['node_ids']))
        return results

    def expand(self,query_entities):
        chunks, paths = set(),[]
        for entity_id in sorted(set(query_entities)):
            if entity_id in self.entities:
                chunks.update(m.chunk_id for m in self.entities[entity_id].mentions)
            for path in self.neighbours(entity_id,2):
                paths.append(path)
                chunks.update(m.chunk_id for m in self.entities[path['entity_id']].mentions)
                for edge in path['edge_ids']:
                    chunks.update(x for x in self.relations[edge].evidence if not x.startswith('geoserver:'))
        return sorted(chunks),paths

    def statistics(self):
        simple = nx.Graph(self.graph)
        return dict(nodes=self.graph.number_of_nodes(),edges=self.graph.number_of_edges(),
                    components=nx.number_connected_components(self.graph),
                    top_degree=sorted(self.graph.degree,key=lambda x:(-x[1],x[0]))[:5],
                    pagerank=nx.pagerank(simple) if simple else {})

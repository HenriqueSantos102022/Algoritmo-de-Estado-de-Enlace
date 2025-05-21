# Algoritmo de Dijkstra para Roteamento de Rede
# ==================================================================
# Este módulo oferece funcionalidade para calcular os caminhos mais curtos 
# entre roteadores de rede usando o algoritmo de Dijkstra. Ele processa um 
# Banco de Dados de Estado de Link (LSDB) para produzir tabelas de roteamento.

from typing import Dict, Any, Set, Optional
import json
from collections import defaultdict

def dijkstra(source_router: str, lsdb: Dict[str, Any]) -> Dict[str, str]:
    """
    Calcula os caminhos mais curtos de um roteador especificado para todos os outros usando o algoritmo de Dijkstra.
    
    Args:
        source_router: O endereço IP do roteador de origem.
        lsdb: Um banco de dados de estado de link contendo detalhes de todos os roteadores e suas 
              conexões com os custos associados.
    
    Returns:
        Uma tabela de roteamento mapeando endereços IP de destino para endereços IP de próximo salto
    """
    # Constrói o grafo a partir do LSDB usando dict comprehension
    graph = {
        router_id: {
            neighbor_ip: cost
            for neighbor_data in lsa["vizinhos"].values()
            for neighbor_ip, cost in [neighbor_data]
            if neighbor_ip in lsdb
        }
        for router_id, lsa in lsdb.items()
    }
    
    # Inicializa as estruturas de dados para o algoritmo
    distances = {router: float('inf') for router in graph}
    distances[source_router] = 0
    previous_nodes = {router: None for router in graph}
    visited_nodes: Set[str] = set()
    
    # Executa o algoritmo de Dijkstra
    while len(visited_nodes) < len(graph):
        # Encontra o nó não visitado com a menor distância
        current_node = min(
            (router for router in graph if router not in visited_nodes),
            key=lambda router: distances[router]
        )
        
        # Marca o nó como visitado
        visited_nodes.add(current_node)
        
        # Atualiza as distâncias para os vizinhos
        for neighbor, cost in graph[current_node].items():
            new_distance = distances[current_node] + cost
            
            if new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                previous_nodes[neighbor] = current_node
    
    # Constrói a tabela de roteamento
    routing_table = {}
    
    for destination in graph:
        # Ignora o próprio roteador de origem ou destinos inalcançáveis
        if destination == source_router or previous_nodes[destination] is None:
            continue
            
        # Encontra o próximo salto para este destino
        next_hop = destination
        while previous_nodes[next_hop] != source_router:
            next_hop = previous_nodes[next_hop]
            
        routing_table[destination] = next_hop
    
    return routing_table


if __name__ == "__main__":
    # Exemplo de LSDB para teste
    test_lsdb = {
        "172.20.2.3": {
            "id": "172.20.2.3",
            "vizinhos": {
                "router1": ["172.20.1.3", 0.0034530162811279297],
                "router3": ["172.20.3.3", 0.0012178421020507812]
            },
            "seq": 13701
        },
        "172.20.3.3": {
            "id": "172.20.3.3",
            "vizinhos": {
                "router2": ["172.20.2.3", 0.003142833709716797],
                "router4": ["172.20.4.3", 0.0016400814056396484]
            },
            "seq": 13351
        },
        "172.20.1.3": {
            "id": "172.20.1.3",
            "vizinhos": {
                "router5": ["172.20.5.3", 0.012853384017944336],
                "router2": ["172.20.2.3", 0.00501561164855957]
            },
            "seq": 13584
        },
        "172.20.5.3": {
            "id": "172.20.5.3",
            "vizinhos": {
                "router1": ["172.20.1.3", 0.005136013031005859],
                "router4": ["172.20.4.3", 0.0030078887939453125]
            },
            "seq": 13675
        },
        "172.20.4.3": {
            "id": "172.20.4.3",
            "vizinhos": {
                "router3": ["172.20.3.3", 0.005071878433227539],
                "router5": ["172.20.5.3", 0.011375188827514648]
            },
            "seq": 13770
        }
    }

    # Executa o algoritmo com o LSDB de teste
    print(dijkstra("172.20.1.3", test_lsdb))

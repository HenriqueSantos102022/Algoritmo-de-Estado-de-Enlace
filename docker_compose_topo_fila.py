# Gerador de Docker Compose para Topologia em Fila
# ====================================================
# Este script produz um arquivo docker-compose.yml que configura uma rede 
# com uma topologia linear, onde cada roteador se conecta apenas aos roteadores 
# vizinhos, criando uma linha reta.

import yaml
import sys
from typing import Dict, List, Any, Tuple

def generate_docker_compose(num_subnets: int) -> Dict[str, Any]:
    
    # Gera a configuração do Docker Compose para a topologia em fila.
    
    docker_compose = {
        'services': {},
        'networks': {}
    }

    # Criar todas as redes usando dict comprehension
    docker_compose['networks'] = {
        f"subnet_{i}": {
            'driver': 'bridge',
            'ipam': {
                'config': [{
                    'subnet': f'172.20.{i}.0/24',
                    'gateway': f'172.20.{i}.1',
                }]
            }
        }
        for i in range(1, num_subnets + 1)
    }

    # Criar roteadores e hosts
    for i in range(1, num_subnets + 1):
        router_name = f"router{i}"
        router_ip = f'172.20.{i}.3'

        # Determinar vizinhos baseado na posição na fila
        neighbors = []
        networks = {f"subnet_{i}": {'ipv4_address': router_ip}}
        
        # Adiciona vizinho anterior se não for o primeiro roteador
        if i > 1:
            neighbors.append(f"[router{i-1}, 172.20.{i-1}.3, 1]")
            networks[f"subnet_{i-1}"] = {'ipv4_address': f'172.20.{i-1}.2'}
            
        # Adiciona vizinho posterior se não for o último roteador
        if i < num_subnets:
            neighbors.append(f"[router{i+1}, 172.20.{i+1}.3, 1]")
            networks[f"subnet_{i+1}"] = {'ipv4_address': f'172.20.{i+1}.4'}

        # Configuração do roteador
        docker_compose['services'][router_name] = {
            'build': {
                'context': './router',
                'dockerfile': 'Dockerfile'
            },
            'volumes': ['./router:/app'],
            'environment': [
                f"vizinhos={','.join(neighbors)}",
                f"my_ip={router_ip}",
                f"my_name={router_name}"
            ],
            'networks': networks,
            'cap_add': ['NET_ADMIN'],
            'command': f'/bin/bash -c "ip route del default && ip route add default via {router_ip} && python router.py"'
        }

        # Gerar hosts para cada subrede usando list comprehension
        host_configs = [
            (f"host{i}{host_id}", f'172.20.{i}.{ip_suffix}')
            for host_id, ip_suffix in [(0, 10), (1, 11)]
        ]
        
        for host_name, host_ip in host_configs:
            docker_compose['services'][host_name] = {
                'build': {
                    'context': './host',
                    'dockerfile': 'Dockerfile'
                },
                'networks': {
                    f"subnet_{i}": {'ipv4_address': host_ip}
                },
                'depends_on': [router_name],
                'command': f'/bin/bash -c "ip route del default && ip route add default via {router_ip} dev eth0 && sleep infinity"',
                'cap_add': ['NET_ADMIN']
            }

    return docker_compose

def save_to_file(data: Dict[str, Any], filename: str) -> None:
    
    # Salva a configuração gerada em um arquivo YAML.
    
    with open(filename, 'w') as file:
        yaml.dump(data, file, default_flow_style=False, sort_keys=False)

if __name__ == "__main__":
    
    # Gera o arquivo docker-compose.yml com a topologia em fila.
    
    try:
        args = sys.argv[1:]
        # Usa operador ternário para simplificar a lógica
        num_subnets = int(args[0]) if args else int(input("Digite o número de sub-redes: "))
        
        if num_subnets < 1:
            raise ValueError("Deve haver pelo menos 1 sub-rede")

        docker_compose = generate_docker_compose(num_subnets)
        save_to_file(docker_compose, 'docker-compose.yml')
        print("Arquivo docker-compose.yml gerado com sucesso!")

    except ValueError as e:
        print(f"Erro: {e}")

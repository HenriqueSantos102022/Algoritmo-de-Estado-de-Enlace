# Gerador Docker Compose para topologia em anel
# ====================================================
# Este script cria um arquivo docker-compose.yml que configura uma rede 
# com uma topologia circular (anel), onde cada roteador se conecta aos 
# roteadores adjacentes, formando um loop completo.

import yaml
import sys
import os
import psutil
from typing import Dict, List, Any, Tuple, Optional

def generate_docker_compose(num_subnets: int, with_hosts: bool = False, max_test_routers: int = 0) -> Dict[str, Any]:

    # Gera a configuração do Docker Compose para a topologia em anel.

    docker_compose = {
        'services': {},
        'networks': {}
    }

    # Detectar recursos do sistema
    total_cpus = os.cpu_count() or 1  # Fallback para 1 se None
    total_memory = psutil.virtual_memory().total // (1024 * 1024)

    # Calcular alocação de recursos
    num_routers = num_subnets
    num_hosts = num_subnets * 2 if with_hosts else 0
    total_containers = num_routers + num_hosts
    
    # Limitar uso de recursos a 80% do total
    max_cpus = total_cpus * 0.8
    max_memory = total_memory * 0.8
    
    # Calcular recursos por container
    effective_containers = (max_test_routers + num_hosts) if max_test_routers > 0 else total_containers
    cpu_per_container = max_cpus / effective_containers
    mem_per_container = f"{int(max_memory / effective_containers)}M"

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

    # Criar roteadores
    for i in range(1, num_subnets + 1):
        router_name = f"router{i}"
        router_ip = f'172.20.{i}.3'

        # Inicializar listas de vizinhos e dicionário de redes
        neighbors = []
        networks = {f"subnet_{i}": {'ipv4_address': router_ip}}

        # Configurar conexões em anel
        # Caso especial: primeiro roteador se conecta ao último
        if i == 1:
            neighbors.append(f"[router{num_subnets}, 172.20.{num_subnets}.3, 1]")
            networks[f"subnet_{num_subnets}"] = {'ipv4_address': f'172.20.{num_subnets}.2'}
        # Caso especial: último roteador se conecta ao primeiro
        elif i == num_subnets:
            neighbors.append(f"[router1, 172.20.1.3, 1]")
            networks[f"subnet_1"] = {'ipv4_address': f'172.20.1.4'}

        # Conexão com o roteador anterior (exceto o primeiro)
        if i > 1:
            neighbors.append(f"[router{i-1}, 172.20.{i-1}.3, 1]")
            networks[f"subnet_{i-1}"] = {'ipv4_address': f'172.20.{i-1}.2'}

        # Conexão com o próximo roteador (exceto o último)
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
            'command': f'/bin/bash -c "ip route del default && ip route add default via {router_ip} && python router.py"',
            'cpus': str(cpu_per_container),
            'mem_limit': mem_per_container
        }

        # Adicionar hosts se solicitado
        if with_hosts:
            # Usar list comprehension para gerar configurações de hosts
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
                    'cap_add': ['NET_ADMIN'],
                    'cpus': str(cpu_per_container),
                    'mem_limit': mem_per_container
                }

    return docker_compose

def save_to_file(data: Dict[str, Any], filename: str) -> None:

    # Salva a configuração gerada em um arquivo YAML.

    with open(filename, 'w') as file:
        yaml.dump(data, file, default_flow_style=False, sort_keys=False)

if __name__ == "__main__":
    
    # Gera o arquivo docker-compose.yml com a topologia em anel.
    
    try:
        args = sys.argv[1:]

        # Usar operadores ternários para simplificar a lógica de entrada
        num_subnets = int(args[0]) if args else int(input("Digite o número de sub-redes: "))
        with_hosts = bool(int(args[1])) if len(args) > 1 else bool(int(input("Deseja incluir hosts nas sub-redes? (1 para sim, 0 para não): ")))
        max_test_routers = int(args[2]) if len(args) > 2 else 0

        if num_subnets < 1:
            raise ValueError("Deve haver pelo menos 1 sub-rede")

        docker_compose = generate_docker_compose(num_subnets, with_hosts, max_test_routers)
        save_to_file(docker_compose, 'docker-compose.yml')
        print("Arquivo docker-compose.yml gerado com sucesso!")

    except ValueError as e:
        print(f"Erro: {e}")

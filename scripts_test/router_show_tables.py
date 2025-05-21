# Exibição da tabela de roteamento
# ==========================================================
# Este script apresenta as tabelas de roteamento para todos os 
# roteadores em execução no ambiente Docker, simplificando a 
# solução de problemas e a validação do estado atual da rede.

import sys
import os
from typing import List

# Cores para output
class Colors:
    # Classe para definição de cores no terminal.
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

def get_router_containers() -> List[str]:
    
    # Obtém todos os containers de roteadores em execução.
    
    # Returns:
    #     Lista ordenada com os nomes dos containers de roteadores
    
    output = os.popen("docker ps --filter 'name=router' --format '{{.Names}}'").read()
    return sorted(output.splitlines())

# Função extract_ mantida sem modificações conforme solicitado
def extract_router_number(container_name):
    # Extrai o número do roteador do nome do container.
    # Tenta encontrar um número após 'router' no nome
    try:
        if '-' in container_name:
            # Formato: nome-router1-1
            parts = container_name.split('-')
            if len(parts) >= 2 and 'router' in parts[1]:
                return parts[1].replace('router', '')
        # Formato alternativo: router1
        elif 'router' in container_name:
            return container_name.replace('router', '')
        # Se não conseguir extrair, retorna o nome completo
        return container_name
    except Exception as e:
        print(f"Erro ao extrair número do roteador: {e}")
        return container_name


def get_routing_table(container: str) -> str:
    
    # Obtém a tabela de roteamento de um container.
    
    # Args:
    #     container: Nome do container do roteador
        
    # Returns:
    #     Tabela de roteamento como string formatada
    
    command = f"docker exec {container} ip route"
    print(f"{Colors.YELLOW}{command}{Colors.NC}")
    result = os.popen(command).read()
    return result.strip()

def main() -> None:
    
    # Função principal que obtém e exibe as tabelas de roteamento de todos os roteadores.
    # Cada tabela é exibida com formatação colorida para facilitar a leitura.
    
    # Obtém os roteadores
    routers = get_router_containers()
    
    # Verifica se existem roteadores em execução
    if not routers:
        print(f"{Colors.RED}Erro: Nenhum roteador está rodando. Execute 'make up' primeiro.{Colors.NC}")
        sys.exit(1)
    
    # Exibe informação sobre os roteadores encontrados
    print(f"{Colors.BLUE}Encontrados {len(routers)} roteadores. Mostrando tabelas de roteamento...{Colors.NC}", end='\n\n')
    
    # Processa cada roteador, ordenando pela numeração
    for router in sorted(routers, key=extract_router_number):
        router_num = extract_router_number(router)
        header = f"=== Tabela de Roteamento do Router {router_num} ==="
        separator = "=" * len(header)
        
        # Exibe cabeçalho formatado
        print(f"{Colors.BOLD}{Colors.CYAN}{header}{Colors.NC}")
        
        # Obtém e exibe a tabela de roteamento
        routing_table = get_routing_table(router)
        
        if routing_table:
            # Destaca a primeira linha da tabela
            lines = routing_table.split('\n')
            print(f"{Colors.YELLOW}{lines[0]}{Colors.NC}")
            
            # Exibe as demais linhas sem formatação especial
            for line in lines[1:]:
                print(line)
        else:
            print(f"{Colors.RED}Nenhuma rota encontrada.{Colors.NC}")
        
        # Exibe separador de rodapé
        print(f"{Colors.BOLD}{Colors.CYAN}{separator}{Colors.NC}", end='\n\n')

if __name__ == "__main__":
    main()

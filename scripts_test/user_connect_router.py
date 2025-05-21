# Avaliação de conectividade de host para roteador
# ==========================================================
# Este script avalia a conectividade entre hosts e roteadores na rede 
# por meio de testes de ping paralelos, confirmando se os hosts podem 
# se comunicar com roteadores que não estão diretamente vinculados.

import os
import threading
import time
import sys
from typing import List, Tuple, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cores para output
class Colors:
    # Classe para definição de cores no terminal.
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[0;33m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

# Configurações de paralelismo baseadas no hardware
CPU_COUNT = os.cpu_count() or 1
# Limitar o número máximo de threads para evitar o erro "can't start new thread"
MAX_THREADS = min(100, CPU_COUNT * 4)  # Limita a no máximo 100 threads

def get_hosts() -> List[str]:
    
    # Obtém a lista de todos os hosts em execução no ambiente Docker.
    
    # Returns:
    #     Lista ordenada com os nomes dos containers de hosts
    
    output = os.popen("docker ps --filter 'name=host' --format '{{.Names}}'").read()
    return sorted(output.splitlines())

def get_routers() -> List[str]:
    """
    # Obtém a lista de todos os roteadores em execução no ambiente Docker.
    
    # Returns:
    #     Lista ordenada com os nomes dos containers de roteadores
    """
    output = os.popen("docker ps --filter 'name=router' --format '{{.Names}}'").read()
    return sorted(output.splitlines())

# Função extract_ mantida sem modificações conforme solicitado
def extract_num_router(container_name):
    # Extrai o número do roteador do nome do container.
    try:
        if '-' in container_name:
            # Formato: network-simulator-router1-1
            parts = container_name.split('-')
            for part in parts:
                if 'router' in part and part.replace('router', '').isdigit():
                    return part.replace('router', '')
        # Formato alternativo: router1
        elif 'router' in container_name and container_name.replace('router', '').isdigit():
            return container_name.replace('router', '')
        # Se não conseguir extrair, retorna 1 como fallback
        print(f"Aviso: Não foi possível extrair número do roteador de {container_name}, usando 1 como padrão")
        return "1"
    except Exception as e:
        print(f"Erro ao extrair número do roteador: {e}")
        return "1"

# Função extract_ mantida sem modificações conforme solicitado
def extract_num_host(container_name):
    # Extrai o número do host do nome do container.
    try:
        if '-' in container_name:
            # Formato: network-simulator-host10-1
            parts = container_name.split('-')
            for part in parts:
                if 'host' in part and part.replace('host', '').isdigit():
                    host_num = part.replace('host', '')
                    if len(host_num) >= 2:
                        return host_num[0], host_num[1]
        # Formato alternativo: host10
        elif 'host' in container_name and container_name.replace('host', '').isdigit():
            host_num = container_name.replace('host', '')
            if len(host_num) >= 2:
                return host_num[0], host_num[1]
        
        # Se não conseguir extrair, retorna valores padrão
        print(f"Aviso: Não foi possível extrair número do host de {container_name}, usando valores padrão")
        return "1", "0"
    except Exception as e:
        print(f"Erro ao extrair número do host: {e}")
        return "1", "0"

def ping_test(source_host: str, target_router: str, router_ip: str) -> Tuple[bool, float]:

    # Executa um ping de um host para um roteador e retorna o resultado.
    
    # Args:
    #     source_host: Nome do container do host de origem
    #     target_router: Nome do container do roteador de destino
    #     router_ip: Endereço IP do roteador para o ping
        
    # Returns:
    #     Tupla contendo (sucesso, tempo_decorrido)

    start_time = time.time()
    command = f"docker exec {source_host} ping -c 1 -W 0.5 {router_ip} > /dev/null 2>&1"
    print(f"{Colors.YELLOW}{command}{Colors.NC}")
    
    exit_code = os.system(command)
    elapsed_time = time.time() - start_time
    is_successful = (exit_code == 0)
    
    return is_successful, elapsed_time

def main() -> None:
    
    # Função principal que coordena o teste de conectividade entre hosts e roteadores.
    # Usa ThreadPoolExecutor para limitar o número de threads simultâneas e evitar
    # o erro "can't start new thread".
    
    # Obtém a lista de roteadores em execução
    routers = get_routers()
    if not routers:
        print(f"{Colors.RED}Erro: nenhum roteador rodando. Execute 'make up'.{Colors.NC}")
        return

    # Obtém a lista de hosts em execução
    hosts = get_hosts()
    if not hosts:
        print(f"{Colors.RED}Erro: nenhum host rodando. Execute 'make up'.{Colors.NC}")
        return
    
    # Gera todas as combinações de pings entre hosts e roteadores
    ping_tasks = [
        (source, target, f"172.20.{extract_num_router(target)}.3") 
        for source in hosts 
        for target in routers
    ]
    
    total_tasks = len(ping_tasks)
    print(f"{Colors.MAGENTA}Iniciando {total_tasks} pings de hosts para roteadores com máximo de {MAX_THREADS} threads simultâneas...{Colors.NC}")
    
    # Inicializa estruturas para armazenar resultados
    results = {}
    
    # Usa ThreadPoolExecutor para limitar o número de threads simultâneas
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Mapeia as tarefas para futures
        future_to_task = {
            executor.submit(ping_test, source, target, ip): (source, target) 
            for source, target, ip in ping_tasks
        }
        
        # Processa os resultados à medida que são concluídos
        completed = 0
        for future in as_completed(future_to_task):
            source, target = future_to_task[future]
            completed += 1
            
            # Exibe progresso a cada 10% concluído
            if completed % max(1, total_tasks // 10) == 0:
                print(f"{Colors.BLUE}Progresso: {completed}/{total_tasks} ({completed/total_tasks*100:.1f}%){Colors.NC}")
            
            try:
                success, time_taken = future.result()
                
                # Inicializa o dicionário para o host se necessário
                if source not in results:
                    results[source] = []
                
                # Adiciona o resultado
                results[source].append((target, success, time_taken))
                
            except Exception as e:
                print(f"{Colors.RED}Erro ao executar ping de {source} para {target}: {e}{Colors.NC}")
    
    # Contadores para estatísticas
    successful_pings = 0
    total_pings = sum(len(results[source]) for source in results)
    
    # Exibe os resultados organizados por host
    for source in sorted(results.keys()):
        print(f"\n{Colors.CYAN}=== Host {source} ==={Colors.NC}")
        
        # Exibe os resultados de cada ping
        for target, success, time_taken in sorted(results[source], key=lambda x: extract_num_router(x[0])):
            status_color = Colors.GREEN if success else Colors.RED
            status_text = "OK" if success else "Falha"
            
            print(f"{status_color}{source} -> {target}: {status_text} ({time_taken:.2f}s){Colors.NC}")
            if success:
                successful_pings += 1
    
    # Exibe estatísticas gerais
    success_rate = (successful_pings / total_pings) * 100 if total_pings > 0 else 0
    print(f"\n{Colors.MAGENTA}Total de pings: {total_pings}, Sucessos: {successful_pings}, Falhas: {total_pings - successful_pings} ({success_rate:.1f}% de sucesso){Colors.NC}")

if __name__ == "__main__":
    main()
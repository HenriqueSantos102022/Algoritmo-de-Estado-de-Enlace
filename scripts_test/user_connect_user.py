# Verificação de conectividade host a host
# ==========================================================
# Este script verifica a conectividade entre todos os hosts na rede 
# usando operações de ping paralelas, garantindo que o roteamento 
# entre sub-redes distintas opere corretamente.

import os
import sys
import threading
import time
from typing import List, Tuple, Dict, Any, Optional
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

# Configurações de ping
PING_RETRIES = 3       # Número de tentativas de ping para cada destino
PING_TIMEOUT = 2       # Timeout em segundos para cada ping
PING_INTERVAL = 0.5    # Intervalo entre tentativas de ping
WAIT_FOR_NETWORK = 5   # Tempo em segundos para aguardar a convergência da rede

def get_hosts() -> List[str]:
    
    # Obtém a lista de todos os hosts em execução no ambiente Docker.
    
    # Returns:
    #     Lista ordenada com os nomes dos containers de hosts
    
    output = os.popen("docker ps --filter 'name=host' --format '{{.Names}}'").read()
    return sorted(output.splitlines())

def get_routers() -> List[str]:
    
    # Obtém a lista de todos os roteadores em execução no ambiente Docker.
    
    # Returns:
    #     Lista ordenada com os nomes dos containers de roteadores
    
    output = os.popen("docker ps --filter 'name=router' --format '{{.Names}}'").read()
    return sorted(output.splitlines())

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

def verify_host_ip(host_name: str) -> Optional[str]:
    
    # Verifica o endereço IP real do host no Docker.
    
    # Args:
    #     host_name: Nome do container do host
        
    # Returns:
    #     Endereço IP do host ou None se não for possível obter
    
    try:
        command = f"docker exec {host_name} hostname -I | awk '{{print $1}}'"
        ip = os.popen(command).read().strip()
        if ip and len(ip.split('.')) == 4:
            return ip
        return None
    except Exception as e:
        print(f"{Colors.RED}Erro ao verificar IP do host {host_name}: {e}{Colors.NC}")
        return None

def ping_test(source_host: str, target_host: str, target_ip: str) -> Tuple[bool, float]:
    
    # Executa um ping de um host para outro com múltiplas tentativas e retorna o resultado.
    
    # Args:
    #     source_host: Nome do container do host de origem
    #     target_host: Nome do container do host de destino
    #     target_ip: Endereço IP do destino para o ping
        
    # Returns:
    #     Tupla contendo (sucesso, tempo_decorrido)
    
    # Verificar se o IP de destino está correto
    verified_ip = verify_host_ip(target_host)
    if verified_ip and verified_ip != target_ip:
        print(f"{Colors.YELLOW}Aviso: IP calculado para {target_host} ({target_ip}) difere do IP real ({verified_ip}){Colors.NC}")
        target_ip = verified_ip
    
    start_time = time.time()
    success = False
    
    # Tentar ping múltiplas vezes
    for attempt in range(PING_RETRIES):
        command = f"docker exec {source_host} ping -c 1 -W {PING_TIMEOUT} {target_ip} > /dev/null 2>&1"
        if attempt > 0:
            print(f"{Colors.YELLOW}Tentativa {attempt+1} para {source_host} -> {target_host} ({target_ip}){Colors.NC}")
        else:
            print(f"{Colors.YELLOW}{command}{Colors.NC}")
        
        exit_code = os.system(command)
        if exit_code == 0:
            success = True
            break
        
        # Aguardar um pouco antes da próxima tentativa
        if attempt < PING_RETRIES - 1:
            time.sleep(PING_INTERVAL)
    
    elapsed_time = time.time() - start_time
    return success, elapsed_time

def check_network_readiness() -> bool:
    
    # Verifica se a rede está pronta para testes, verificando se os roteadores
    # estão respondendo e se as tabelas de roteamento estão configuradas.
    
    # Returns:
    #     True se a rede parece estar pronta, False caso contrário
    
    routers = get_routers()
    if not routers:
        print(f"{Colors.RED}Erro: nenhum roteador encontrado.{Colors.NC}")
        return False
    
    print(f"{Colors.BLUE}Verificando prontidão da rede com {len(routers)} roteadores...{Colors.NC}")
    
    # Verificar se os roteadores estão respondendo
    for router in routers:
        command = f"docker exec {router} ping -c 1 -W 1 127.0.0.1 > /dev/null 2>&1"
        exit_code = os.system(command)
        if exit_code != 0:
            print(f"{Colors.RED}Roteador {router} não está respondendo.{Colors.NC}")
            return False
    
    # Verificar se as tabelas de roteamento têm entradas
    for router in routers:
        command = f"docker exec {router} ip route | grep -v '172.20' | wc -l"
        route_count = int(os.popen(command).read().strip() or "0")
        if route_count < 2:  # Pelo menos algumas rotas além da rede local
            print(f"{Colors.YELLOW}Aviso: Roteador {router} tem poucas rotas configuradas ({route_count}).{Colors.NC}")
    
    print(f"{Colors.GREEN}Verificação de rede concluída. Aguardando {WAIT_FOR_NETWORK}s para convergência...{Colors.NC}")
    time.sleep(WAIT_FOR_NETWORK)
    return True

def main() -> None:
    
    # Função principal que coordena o teste de conectividade entre hosts.
    # Usa ThreadPoolExecutor para limitar o número de threads simultâneas e evitar
    # o erro "can't start new thread".
    
    # Obtém a lista de hosts em execução
    hosts = get_hosts()
    
    # Verifica se existem hosts em execução
    if not hosts:
        print(f"{Colors.RED}Erro: nenhum host rodando. Execute 'make up'.{Colors.NC}")
        return
    
    # Verificar se a rede está pronta
    if not check_network_readiness():
        print(f"{Colors.YELLOW}Aviso: A rede pode não estar totalmente convergida. Continuando mesmo assim...{Colors.NC}")
    
    # Gera todas as combinações de pings entre hosts usando list comprehension
    ping_tasks = []
    
    # Primeiro, verificar os IPs reais dos hosts
    host_ips = {}
    for host in hosts:
        ip = verify_host_ip(host)
        if ip:
            host_ips[host] = ip
            subnet_id, host_id = extract_num_host(host)
            expected_ip = f"172.20.{subnet_id}.1{host_id}"
            if ip != expected_ip:
                print(f"{Colors.YELLOW}Aviso: IP real de {host} é {ip}, diferente do esperado {expected_ip}{Colors.NC}")
    
    # Gerar tarefas de ping com IPs verificados
    for source in hosts:
        for target in hosts:
            if source != target:
                # Usar IP verificado se disponível, caso contrário usar o calculado
                if target in host_ips:
                    target_ip = host_ips[target]
                else:
                    subnet_id, host_id = extract_num_host(target)
                    target_ip = f"172.20.{subnet_id}.1{host_id}"
                
                ping_tasks.append((source, target, target_ip))
    
    total_tasks = len(ping_tasks)
    print(f"{Colors.MAGENTA}Iniciando {total_tasks} pings entre hosts com máximo de {MAX_THREADS} threads simultâneas...{Colors.NC}")
    
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
        for target, success, time_taken in sorted(results[source], key=lambda x: extract_num_host(x[0])[0]):
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

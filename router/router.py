# Implementação de roteador com algoritmo de estado de enlace (Link State)
# ==================================================================
# Este módulo abrange toda a lógica essencial necessária para desenvolver 
# um roteador que emprega o algoritmo Link State para identificar caminhos 
# ideais dentro de uma rede de computadores.

import json
import os
import socket
import threading
import time
import subprocess
from typing import Dict, Tuple, Any
from formatador import Formatter
from algoritmo_dijkstra import dijkstra

# Constantes globais obtidas de variáveis de ambiente
ROUTER_IP = os.getenv("my_ip")
ROUTER_NAME = os.getenv('my_name')
NEIGHBORS = Formatter.formatar_vizinhos(os.getenv("vizinhos"))

# Porta padrão para comunicação LSA
LSA_PORT = 5000

class Logger:
    """Classe para gerenciar logs do roteador."""

    @staticmethod    
    def log(message: str) -> None:  
        """
        Registra uma mensagem de log com timestamp e IP do roteador.
        
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[{timestamp}] [{ROUTER_IP}] {message}", flush=True)

class NetworkUtils:
    """Classe para utilitários de rede."""
    
    @staticmethod
    def _test_ping(ip: str, result: Dict[str, Tuple[bool, float]], thread_lock: threading.Lock) -> None:
        """
        Testa a conectividade com um IP via ping.
        
        Args:
            ip: Endereço IP a ser testado
            result: Dicionário para armazenar os resultados do ping
            thread_lock: Lock para acesso seguro ao dicionário de resultados
        """
        start_time = time.time()
        
        try:
            # Uso de subprocess.run com parâmetros nomeados para maior clareza
            is_alive = subprocess.run(
                ["ping", "-c", "5", "-W", "1", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).returncode == 0
        except Exception:
            is_alive = False
        finally:
            end_time = time.time()
            
        with thread_lock:
            result[ip] = (is_alive, end_time - start_time)
    
    @staticmethod
    def perform_pings(neighbors: Dict[str, Tuple[str, int]]) -> Dict[str, Tuple[str, float]]:
        """
        Executa pings para todos os vizinhos em paralelo e retorna os ativos.
        
        """
        result = {}
        thread_lock = threading.Lock()
        threads = []
        
        # Cria e inicia todas as threads de ping
        for neighbor_name, (ip, _) in neighbors.items():
            thread = threading.Thread(
                target=NetworkUtils._test_ping, 
                args=(ip, result, thread_lock)
            )
            thread.daemon = True
            thread.start()
            threads.append((neighbor_name, ip, thread))

        # Aguarda todas as threads e coleta resultados
        [thread.join() for _, _, thread in threads]
        
        # Usa dict comprehension para criar o dicionário de vizinhos ativos
        return {
            neighbor_name: (ip, ping_duration) 
            for neighbor_name, ip, _ in threads 
            if result.get(ip, (False, 0))[0]  # Filtra apenas os que estão ativos
            for _, ping_duration in [result.get(ip)]  # Extrai a duração do ping
        }

class LSAHandler:
    """Classe para manipulação de LSA (Link State Advertisement)."""
    
    @staticmethod
    def create_lsa_packet(router_id: str, sequence_num: int, neighbors: Dict[str, Tuple[str, float]]) -> Dict[str, Any]:    
        """
        Cria um pacote LSA com informações atuais do roteador.
        
        """
        try:
            # Uso de dict comprehension para criar o pacote
            return {
                "id": router_id,
                "vizinhos": {name: (ip, cost) for name, (ip, cost) in neighbors.items()},
                "seq": sequence_num
            }
        except Exception as e:
            Logger.log(f"Erro ao criar pacote LSA: {e}")
            return {}
        
    @staticmethod
    def send_lsa_to_neighbor(sock: socket.socket, message: bytes, neighbor_name: str, ip: str) -> bool:
        """
        Envia um LSA para um vizinho específico.
        
        Args:
            sock: Socket UDP para envio
            message: Mensagem LSA serializada
            neighbor_name: Identificador do vizinho
            ip: Endereço IP do vizinho
            
        Returns:
            True se o envio foi bem sucedido, False caso contrário
        """
        try:
            sock.sendto(message, (ip, LSA_PORT))
            return True
        except Exception as e:
            Logger.log(f"Erro ao enviar LSA para {neighbor_name} ({ip}): {e}")
            return False
        
class NetworkInterface:
    """Classe para gerenciar interfaces de rede e tabelas de roteamento."""
    
    @staticmethod
    def _extract_network_prefix(ip_address: str) -> str:
        """
        Extrai o prefixo de rede de um endereço IP.
        
        Args:
            ip_address: Endereço IP (ex: 172.20.5.10)
            
        Returns:
            Prefixo de rede com máscara (ex: 172.20.5.0/24)
        """
        # Uso de list slicing para extrair os primeiros 3 octetos
        network_prefix = '.'.join(ip_address.split('.')[:3])
        return f"{network_prefix}.0/24"
    
    @staticmethod
    def get_existing_routes(routes: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
        
        # Recupera todas as rotas atuais do sistema e as compara com um conjunto de novas rotas.
        
        # Args:
        #     routes: Um dicionário que especifica as novas rotas a serem configuradas, 
        #         mapeando IPs de destino para IPs do próximo salto.
        
        # Returns:
        #     Tuple contendo:
        #         - Um dicionário de novas rotas a serem adicionadas.
        #         - Um dicionário de rotas a serem excluídas.
        #         - Um dicionário de rotas a ser atualizado.
        
        try:
            # Padroniza formato das novas rotas usando dict comprehension
            new_routes = {
                NetworkInterface._extract_network_prefix(destination): next_hop
                for destination, next_hop in routes.items()
            }
            
            # Obtém rotas existentes do sistema
            result = subprocess.run(
                ["ip", "route", "show"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Inicializa dicionários para armazenar rotas
            existing_routes = {}
            system_routes = {}
            
            # Processa cada linha do resultado
            for line in result.stdout.splitlines():
                parts = line.split()
                
                # Usa operador ternário para simplificar a lógica
                if parts[0] != "default" and parts[1] == "via":
                    existing_routes[parts[0]] = parts[2]  # network, next_hop
                elif parts[1] == 'dev':
                    system_routes[parts[0]] = parts[-1]  # network, interface
            
            # Usa dict comprehensions para identificar rotas a adicionar, remover e substituir
            routes_to_replace = {
                network: next_hop 
                for network, next_hop in new_routes.items()
                if network in existing_routes and existing_routes[network] != next_hop
            }
            
            routes_to_add = {
                network: next_hop 
                for network, next_hop in new_routes.items()
                if network not in existing_routes and network not in system_routes
            }
            
            routes_to_remove = {
                network: next_hop 
                for network, next_hop in existing_routes.items()
                if network not in new_routes
            }
                    
            return routes_to_add, routes_to_remove, routes_to_replace
        
        except Exception as e:
            Logger.log(f"Erro ao obter rotas existentes: {e}")
            return {}, {}, {}
        
    @staticmethod
    def add_route(destination: str, next_hop: str) -> None:
        """
        Configura a interface de rede para o próximo salto.
        
        Args:
            destination: Endereço IP de destino (exemplo: 172.20.5.5)
            next_hop: Endereço IP do próximo salto (exemplo: 172.20.1.5)
        """
        try:
            network = NetworkInterface._extract_network_prefix(destination)
            command = f"ip route add {network} via {next_hop}"
            
            process = subprocess.run(
                command.split(),
                capture_output=True,
            )
            
            # Uso de operador ternário para simplificar a lógica de log
            message = (
                f"Rota adicionada: {network} via {next_hop}" 
                if process.returncode == 0 
                else f"Erro ao adicionar rota: {process.stderr.decode()}"
            )
            Logger.log(message)
            
        except Exception as e:
            Logger.log(f"Erro ao adicionar rota: {e}")

    @staticmethod
    def remove_route(destination: str) -> None:
        """
        Remove a configuração da interface de rede.
        
        """
        try:
            process = subprocess.run(["ip", "route", "del", destination], check=True)
            
            # Uso de operador ternário para simplificar a lógica de log
            message = (
                f"Rota removida: {destination}" 
                if process.returncode == 0 
                else f"Erro ao remover rota: {process.stderr.decode()}"
            )
            Logger.log(message)
            
        except Exception as e:
            Logger.log(f"Erro ao remover rota: {e}")
    
    @staticmethod        
    def save_lsdb_and_routes(lsdb: Dict[str, Any], routes: Dict[str, str]) -> None:
        """
        Salva a LSDB e tabela de rotas em arquivos JSON.
        
        """
        try:
            # Criar os diretórios se não existirem
            for directory in ['lsdb', 'rotas']:
                os.makedirs(directory, exist_ok=True)

            # Usa with para garantir que os arquivos sejam fechados corretamente
            with open(f"lsdb/lsdb_{ROUTER_NAME}.json", "w") as file:
                json.dump(lsdb, file, indent=4)
                
            with open(f"rotas/rotas_{ROUTER_NAME}.json", "w") as file:
                json.dump(routes, file, indent=4)
                
        except Exception as e:
            Logger.log(f"Erro ao salvar LSDB e rotas: {e}")
            
    @staticmethod
    def replace_route(destination: str, next_hop: str) -> None:
        """
        Substitui a configuração existente de interface de rede.
        
        """
        try:
            network = NetworkInterface._extract_network_prefix(destination)
            command = f"ip route replace {network} via {next_hop}"
            
            process = subprocess.run(command.split(), check=True)
            
            # Uso de operador ternário para simplificar a lógica de log
            message = (
                f"Rota alterada: {network} via {next_hop}" 
                if process.returncode == 0 
                else f"Erro ao substituir rota: {process.stderr.decode()}"
            )
            Logger.log(message)
            
        except Exception as e:
            Logger.log(f"Erro ao substituir rota: {e}")
    
    @staticmethod
    def configure_interfaces(lsdb: Dict[str, Any], active_neighbors: Dict[str, Tuple[str, float]]) -> None:
        """
        Configura as interfaces de rede com base na LSDB e vizinhos ativos.
        
        """
        # Calcula rotas usando o algoritmo de Dijkstra
        routes = dijkstra(ROUTER_IP, lsdb)
        NetworkInterface.save_lsdb_and_routes(lsdb, routes)
        
        # Cria um conjunto de IPs de vizinhos ativos para busca eficiente
        neighbor_ips = {ip for _, (ip, _) in active_neighbors.items()}
        
        # Filtra rotas válidas (aquelas cujo próximo salto é um vizinho ativo)
        valid_routes = {
            destination: next_hop 
            for destination, next_hop in routes.items() 
            if next_hop in neighbor_ips
        }
        
        # Obtém as alterações necessárias na tabela de roteamento
        routes_to_add, routes_to_remove, routes_to_replace = NetworkInterface.get_existing_routes(valid_routes)
        
        # Aplica as alterações
        for destination in routes_to_remove:
            NetworkInterface.remove_route(destination)
                
        for destination, next_hop in routes_to_add.items():
            NetworkInterface.add_route(destination, next_hop)
                
        for destination, next_hop in routes_to_replace.items():
            NetworkInterface.replace_route(destination, next_hop)

class Router:
    """Classe principal do roteador."""
    
    def __init__(self):
        """Inicializa o roteador e suas dependências."""
        # Configurações obtidas de variáveis de ambiente
        self.lsdb = {}  # Link State Database
        self.active_neighbors = {}
        self.lock = threading.Lock()
        
        Logger.log(f"Roteador inicializado com Nome: {ROUTER_IP}")
        Logger.log(f"Vizinhos configurados: {NEIGHBORS}")
    
    def has_neighbors_changed(self, previous_neighbors: Dict[str, Tuple[str, float]], current_neighbors: Dict[str, Tuple[str, float]]) -> bool:
        """
        Compara os vizinhos ativos com os anteriores e retorna True se houver diferença.
        
        """
        # Verifica se o número de vizinhos mudou
        if len(previous_neighbors) != len(current_neighbors):
            return True
        
        # Usa a função any para verificar se algum vizinho mudou
        return any(
            neighbor not in previous_neighbors or previous_neighbors[neighbor] != (ip, cost)
            for neighbor, (ip, cost) in current_neighbors.items()
        )
            
    def send_lsa_thread(self) -> None:
        """Thread para enviar LSAs periodicamente."""
        # Configura o socket UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sequence_num = 0
        
        while True:
            # Verifica vizinhos ativos
            current_neighbors = NetworkUtils.perform_pings(NEIGHBORS)
            
            # Se houve mudança nos vizinhos, atualiza e propaga as informações
            if self.has_neighbors_changed(self.active_neighbors, current_neighbors):
                sequence_num += 1
                lsa_packet = LSAHandler.create_lsa_packet(ROUTER_IP, sequence_num, current_neighbors) 
                message = json.dumps(lsa_packet).encode()
                
                # Envia LSA para todos os vizinhos ativos
                for neighbor, (ip, _) in current_neighbors.items():
                    LSAHandler.send_lsa_to_neighbor(sock, message, neighbor, ip)
  
                # Atualiza o estado local e reconfigura interfaces
                with self.lock:
                    self.lsdb[ROUTER_IP] = lsa_packet
                    self.active_neighbors = current_neighbors
                    NetworkInterface.configure_interfaces(self.lsdb, self.active_neighbors)
                
    def receive_lsa_thread(self) -> None:
        """Thread para receber LSAs de outros roteadores."""
        # Configura o socket UDP para recebimento
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind(("0.0.0.0", LSA_PORT))
        except Exception as e:
            Logger.log(f"Erro ao vincular socket: {e}")
            return
            
        while True:
            try:
                # Recebe pacote LSA
                data, addr = sock.recvfrom(4096)
                lsa_packet = json.loads(data.decode())
                source_router = lsa_packet["id"]
                sender_ip = addr[0]

                # Atualiza LSDB apenas se o pacote for mais recente
                is_new_or_updated = (
                    source_router not in self.lsdb or 
                    lsa_packet["seq"] > self.lsdb[source_router]["seq"]
                )
                
                if is_new_or_updated:
                    # Encaminha o LSA para todos os vizinhos exceto o remetente
                    for neighbor, (ip, _) in self.active_neighbors.items():
                        if ip != sender_ip:
                            LSAHandler.send_lsa_to_neighbor(sock, data, neighbor, ip)
                    
                    # Atualiza a LSDB e reconfigura interfaces
                    with self.lock:
                        self.lsdb[source_router] = lsa_packet
                        NetworkInterface.configure_interfaces(self.lsdb, self.active_neighbors)
                        
            except Exception as e:
                Logger.log(f"Erro ao processar LSA recebido: {e}")
    
    def start(self) -> None:
        """Inicia o roteador e suas threads."""
        # Cria e inicia as threads
        threads = [
            threading.Thread(target=self.send_lsa_thread, daemon=True),
            threading.Thread(target=self.receive_lsa_thread, daemon=True)
        ]
        
        # Inicia todas as threads
        for thread in threads:
            thread.start()
        
        Logger.log("Roteador iniciado com sucesso")
        
        # Mantém o programa em execução
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            Logger.log("Roteador encerrado pelo usuário")

if __name__ == "__main__":
    router = Router()
    router.start()

# Utilitários de formatação de dados para operações de roteador
# ==================================================================
# Este módulo oferece funções e classes para formatar dados usados 
# pelo roteador na implementação do algoritmo Link State.

from typing import Dict, Tuple, Optional

class Formatter:
    """Classe para formatação de dados do roteador."""
    
    @staticmethod
    def formatar_vizinhos(neighbors_str: Optional[str]) -> Dict[str, Tuple[str, int]]:
        """
        Formata a string de vizinhos em um dicionário estruturado.
        
        Args:
            neighbors_str: String no formato "[router1, 172.20.1.2, 1],[router3, 172.20.3.2, 1]"
            
        Returns:
            Dicionário formatado com vizinhos no formato {nome: (ip, custo)}
        """
        # Retorna dicionário vazio se a string for vazia
        if not neighbors_str:
            return {}
            
        # Divide a string em entradas individuais de vizinhos
        neighbor_entries = neighbors_str.strip("[]").split("],[")
        
        # Usa dict comprehension para criar o dicionário de vizinhos
        return {
            parts[0].strip(): (parts[1].strip(), int(parts[2].strip()))
            for entry in neighbor_entries
            for parts in [entry.split(",")]
            if len(parts) >= 3
        }

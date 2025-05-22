
# Implementação do Algoritmo de Estado de Enlace com Docker e Python

## Universidade Federal do Piauí - Campus Senador Helvídio Nunes de Barros  
**Curso de Bacharel em Sistemas de Informação**  
**Disciplina: Redes de Computadores II**  

---

## 📖 Sobre o projeto

Este trabalho desenvolve uma simulação de uma rede de computadores formada por **hosts** e **roteadores**, utilizando as tecnologias **Python** e **Docker**.  
Os roteadores adotam o algoritmo de roteamento baseado em **estado de enlace (Link State Routing Algorithm)**, possibilitando uma comunicação eficiente entre hosts localizados em sub-redes distintas.

---

## 🎯 Objetivos

- Simular uma rede composta por diversas sub-redes, cada uma com dois hosts e um roteador.
- Construir topologias interligando os roteadores (em **fila** ou **anel**).
- Implementar o algoritmo de roteamento por estado de enlace em cada roteador.
- Manter atualizadas a **LSDB** (Link State Database) e a tabela de roteamento.
- Utilizar **threads** para envio e recebimento de pacotes de estado de enlace.
- Comunicar roteadores via **UDP** ou **TCP**.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3**: lógica dos roteadores e hosts.
- **Docker & Docker Compose**: criação e simulação de ambientes isolados.
- **Threading**: concorrência e execução paralela.
- **Socket UDP**: envio e recebimento de pacotes LSA.
- **ip route**: gerenciamento das rotas.

---

## ▶️ Como executar o projeto

### ✅ Pré-requisitos
- Docker >= 20.10
- Docker Compose >= 2.0
- Python >= 3.8
- Make (opcional)

### 🚀 Passo a Passo

1️⃣ Clone o repositório:
```bash
git clone https://link-para-o-projeto
cd nome_do_repositorio
```

2️⃣ Gere a topologia desejada:

- **Topologia em Anel**:
```bash
make gerar_topologia_anel
# ou
python3 docker_compose_topo_anel.py
```

- **Topologia em Fila**:
```bash
make gerar_topologia_fila
# ou
python3 docker_compose_topo_fila.py
```

> 📝 Insira o número de sub-redes conforme solicitado.

3️⃣ Inicie os containers:
```bash
make up
# ou
docker compose up --build
```

4️⃣ Aguarde o tempo de convergência (configuração das tabelas de roteamento).

5️⃣ Verifique a tabela de roteamento:
```bash
make router-show-tables
# ou
python3 scripts_test/router_show_tables.py
```

6️⃣ Teste a conectividade entre roteadores:
```bash
make router-connect-router
# ou
python3 scripts_test/router_connect_router.py
```

7️⃣ Teste a conectividade entre hosts e roteadores:
```bash
make user-connect-router
# ou
python3 scripts_test/user_connect_router.py
```

8️⃣ Teste a conectividade entre hosts:
```bash
make user-connect-user
# ou
python3 scripts_test/user_connect_user.py
```

9️⃣ Encerre os containers:
```bash
make down
# ou
docker compose down
```

🔟 Remova imagens e volumes:
```bash
make clear
# ou
docker compose down --rmi all --volumes --remove-orphans
docker network prune -f
```

---

## 📡 Justificativa do Protocolo Escolhido

O protocolo **UDP** foi escolhido para a comunicação entre roteadores por:

✅ Menor latência e overhead.  
✅ Otimização para mensagens curtas (como pacotes de roteamento).  
✅ Suporte nativo a **multicast**.  
✅ Transmissão contínua sob carga.

Apesar do **TCP** garantir confiabilidade, sua complexidade e latência poderiam prejudicar a agilidade na propagação de informações de roteamento.

---

## 🏗️ Como a Topologia foi Construída

- **Scripts**: `docker_compose_topo_anel.py` e `docker_compose_topo_fila.py`.
- Criam sub-redes (cada uma com 1 roteador e 2 hosts).
- Configuram conexões e endereços IP automaticamente.
- Geram o arquivo `docker-compose.yml`.

**Topologias**:

- **Fila (linear)**: roteadores conectados a vizinhos diretos.  
- **Anel (circular)**: adiciona conexão entre primeiro e último roteadores.

---

## 🖧 Exemplo de Configuração de Sub-redes

```yaml
networks:
  subnet_1:
    ipv4_address: 172.20.1.3
  subnet_20:
    ipv4_address: 172.20.20.2
  subnet_2:
    ipv4_address: 172.20.2.4
```

---

## 🚦 Configuração do Roteador

- **build**: contexto e Dockerfile (`./router`).
- **volumes**: monta o código-fonte no container.
- **environment**: define vizinhos e IPs.  
- **networks**: especifica sub-redes e IPs.  
- **cap_add**: adiciona `NET_ADMIN` para manipular rotas.  
- **command**: remove rota padrão, adiciona personalizada e executa `router.py`.  
- **cpus**: limita uso da CPU.  

```yaml
router1:
  build:
    context: ./router
    dockerfile: Dockerfile
  volumes:
    - ./router:/app
  environment:
    - vizinhos=[router20, 172.20.20.3, 1],[router2, 172.20.2.3, 1]
    - my_ip=172.20.1.3
    - my_name=router1
  networks:
    subnet_1:
      ipv4_address: 172.20.1.3
    subnet_20:
      ipv4_address: 172.20.20.2
    subnet_2:
      ipv4_address: 172.20.2.4
  cap_add:
    - NET_ADMIN
  command: /bin/bash -c "ip route del default && ip route add default via 172.20.1.3 && python router.py"
  cpus: '0.16'
  mem_limit: 51M
```

---

> ✅ **Projeto acadêmico desenvolvido para a disciplina de Redes de Computadores II.**  
> 🖥️ **Simulação de redes e roteamento com tecnologias modernas!**

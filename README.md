
# Implementação do Algoritmo de Estado de Enlace com Docker e Python

## Universidade Federal do Piauí - Campus Senador Helvídio Nunes de Barros

### Curso de Bacharel em Sistemas de Informação  
### Disciplina: Redes de Computadores II


## Sobre o projeto

Este trabalho desenvolve uma simulação de uma rede de computadores formada por hosts e roteadores, utilizando as tecnologias Python e Docker. Os roteadores adotam o algoritmo de roteamento baseado em estado de enlace (Link State Routing Algorithm), possibilitando uma comunicação eficiente entre hosts localizados em subredes distintas.


## Objetivos

- Simular uma rede composta por diversas subredes, sendo que cada subrede inclui dois hosts e um roteador.
- Construir topologias interligando os roteadores, garantindo ao menos uma conectividade parcial (como em fila ou anel).
- Implementar o algoritmo de roteamento por estado de enlace em cada roteador da rede.
- Manter atualizadas a base de dados de estado de enlace (LSDB) e a tabela de roteamento de cada roteador.
- Utilizar threads para lidar com o envio e o recebimento de pacotes de estado de enlace.
- Estabelecer a comunicação entre roteadores por meio dos protocolos UDP ou TCP.

## Tecnologias utilizadas

- Python 3: Responsável pelo desenvolvimento da lógica de funcionamento dos roteadores e hosts.
- Docker e Docker Compose: Utilizados para a criação e simulação dos componentes da rede em ambientes isolados.
- Biblioteca Threading: Aplicada para implementar concorrência, permitindo a execução paralela de tarefas.
- Socket UDP: Empregado na comunicação entre roteadores para o envio e recebimento de pacotes LSA.
- Comando ip route: Utilizado para gerenciar e atualizar a tabela de roteamento dentro dos roteadores.
## Como executar o projeto

Pré-requisitos

- Docker (versão 20.10 ou superior)
- Docker Compose (versão 2.0 ou superior)
- Python 3.8 ou superior
- Make (opcional, para usar os comandos do Makefile)

Passo a Passo para executar o trabalho

#### 1. Clone o repositório:

```bash
  git clone https://link-para-o-projeto
  cd nome_do_repositorio
```

#### 2. Escolha e gere a topologia desejada:

#### Para a topologia em anel:

```bash
  make gerar_topologia_anel
```

#### ou

```bash
  python3 docker_compose_topo_anel.py
```

#### Para a topologia em fila:

```bash
  make gerar_topologia_fila
```

#### ou

```bash
  python3 docker_compose_topo_fila.py
```

##### Quando solicitado, insira o número de subredes que devem compor a rede.

#### 3. Inicie os containers:

```bash
  make up
```

##### 4. Tempo de convergência: Após o início dos containers, aguarde aproximadamente um minuto para que as tabelas de roteamento sejam configuradas entre os roteadores.

#### 5. Faça a verificação da tabela de roteamento:

```bash
  make router-show-tables
```

#### 6. Teste a conectividade entre roteadores:

```bash
  make router-connect-router
```

#### 7. Teste a conectividade entre hosts e roteadores:

```bash
  make user-connect-router
```

#### 8. Teste a conectividade entre hosts:

```bash
  make user-connect-user
```

#### 9. Para encerrar os containers:

```bash
  make down
```

#### 10. Para remover imagens e volumes:

```bash
  make clear
```



## Justificativa do protocolo escolhido

Optou-se pelo uso do protocolo UDP para a troca de informações entre roteadores devido às suas características que favorecem desempenho e simplicidade na comunicação de estado de enlace:

- Menor latência e overhead: O UDP é um protocolo sem conexão, o que elimina a necessidade de handshake e reduz a sobrecarga nos pacotes trocados.
- Adequado para tempo real: Em cenários como o roteamento dinâmico, a perda eventual de um pacote é aceitável, desde que as atualizações sejam frequentes e rápidas.
- Desempenho otimizado para mensagens curtas: Como os pacotes de atualização de roteamento são pequenos e transmitidos periodicamente, o UDP se encaixa perfeitamente nesse tipo de tráfego.
- Facilidade no envio para múltiplos roteadores: O suporte nativo a multicast torna o UDP ideal para distribuir as atualizações simultaneamente a todos os vizinhos.
- Transmissão contínua mesmo sob carga: Por não implementar mecanismos de controle de congestionamento, o UDP permite que as mensagens de atualização continuem sendo enviadas mesmo quando a rede estiver sobrecarregada.

Apesar do TCP garantir a entrega de pacotes, sua complexidade e atraso no estabelecimento de conexões poderiam comprometer a agilidade na propagação das informações de roteamento. Em protocolos de estado de enlace, a prioridade é a rapidez na disseminação das mudanças, e não a confiabilidade absoluta de cada pacote individual.
## Como a topologia foi construída

A criação da topologia da rede é realizada pelos scripts docker_compose_topo_anel.py e docker_compose_topo_fila, responsáveis por:

- Criar diversas sub-redes, cada uma composta por 1 roteador e 2 hosts.

- Estabelecer os vínculos entre os roteadores com base no tipo de topologia selecionado.

- Configurar automaticamente os endereços IP e as rotas estáticas iniciais.

- Gerar o arquivo docker-compose.yml com toda a infraestrutura necessária para iniciar os containers.

Cada topologia apresenta um arranjo distinto entre os roteadores:

- Fila (linear): Cada roteador é conectado apenas aos seus vizinhos diretos, formando uma estrutura em linha.

- Anel (circular): Semelhante à topologia em fila, mas com uma conexão extra entre o primeiro e o último roteador, fechando um circuito contínuo.

## Exemplo de Configuração de Sub-redes

#### Netowrks:

- Representa as redes virtuais criadas para interligar os containers.

- Cada sub-rede utiliza o driver bridge para simular uma rede isolada entre os componentes.

#### Subnet:

- Especifica o intervalo de endereços IP disponível para aquela sub-rede.

- Define também o gateway padrão, permitindo a comunicação entre os dispositivos da mesma rede.

```yaml
  networks:
      subnet_1:
        ipv4_address: 172.20.1.3
      subnet_20:
        ipv4_address: 172.20.20.2
      subnet_2:
        ipv4_address: 172.20.2.4
```

#### Router

Abaixo está a descrição dos principais campos utilizados para configurar o container de um roteador:

- build

Especifica o diretório de contexto e o Dockerfile a ser usado para construir a imagem do roteador.
No nosso caso, o diretório ./router contém tanto o código quanto o Dockerfile responsável pela construção.

- volumes

Monta o diretório local ./router dentro do container, permitindo que o código-fonte seja acessado e executado diretamente.

- environment

Define variáveis de ambiente essenciais, como o nome do roteador, seus vizinhos e os respectivos IPs para comunicação.

- networks

Especifica as sub-redes às quais o roteador está conectado. Cada rede define um IP exclusivo para o roteador dentro daquela sub-rede.

- ipv4_address

Atribui manualmente um IP ao roteador em cada sub-rede. No exemplo, o router1 pode ter vários IPs:

- Endereços terminados em .2 representam os IPs dos roteadores anteriores.

- Endereços terminados em .3 são os IPs do próprio roteador.

- Endereços terminados em .4 pertencem aos roteadores seguintes.
---
- cap_add

Adiciona permissões especiais ao container, como NET_ADMIN, que permite alterar tabelas de roteamento e configurar interfaces de rede.

- command

Define o comando que será executado ao iniciar o container.
Nesse caso, remove a rota padrão do sistema, adiciona uma nova rota padrão personalizada e depois inicia o script principal do roteador.

- cpus

Restringe o uso de CPU pelo container. No exemplo citado, o uso total da CPU está limitado a 80%, somando todos os containers ativos.

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
    command: /bin/bash -c "ip route del default && ip route add default via 172.20.1.3
      && python router.py"
    cpus: '0.16000000000000003'
    mem_limit: 51M
```

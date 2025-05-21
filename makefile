up:
	@docker compose down --remove-orphans
	@echo "start" > router/start.txt
	@docker compose up

gerar_topologia_fila:
	@python3 docker_compose_topo_fila.py

gerar_topologia_anel:
	@python3 docker_compose_topo_anel.py $(qtd) ${with_host} ${qtd_max_test}

down:
	@docker compose down --remove-orphans
	@echo "" > router/start.txt

clear:
	@docker compose down --rmi all --volumes --remove-orphans
	@docker network prune -f

router-show-tables:
	@python3 scripts_test/router_show_tables.py

router-connect-router:
	@python3 scripts_test/router_connect_router.py

user-connect-router:
	@python3 scripts_test/user_connect_router.py

user-connect-user:
	@python3 scripts_test/user_connect_user.py

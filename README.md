# Foodgram

![example workflow](https://github.com/artamon0v/foodgram-project-react/actions/workflows/foodgram_workflow.yml/badge.svg)

### Описание:

Проект Foodgram «Продуктовый помощник» - онлайн-сервис, где пользователи могут публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное», а перед походом в магазин скачивать сводный список продуктов, необходимых для приготовления одного или нескольких выбранных блюд.

### Технологии:

Python
Django REST Framework
API REST
Postman
Djoser
Docker

### Главная страница

http://84.252.139.111/recipes


### Админка

http://84.252.139.111/admin

### Документация

http://84.252.139.111/api/docs/

### Данные для админки

Логин: test@mail.ru
Пароль: admin

### Локальная установка

###### Клонируйте репозиторий:

```
git clone git@github.com:artamon0v/foodgram-project-react.git
```
###### Установите docker на сервер:

```
sudo apt install docker.io 
```

###### Установите docker-compose на сервер: 

```
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

###### Создайте файл .env и поместите в него:

```
cd foodgram-project-react/infra
touch .env

SECRET_KEY
DB_ENGINE
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
```

###### Разверните контейнеры и выполните миграции:

```
sudo docker-compose up -d --build
sudo docker-compose exec backend python manage.py migrate
```

###### Создайте суперюзера:

```
sudo docker-compose exec backend python manage.py createsuperuser
```

###### Соберите статику

```
sudo docker-compose exec backend python manage.py collectstatic --no-input
```

###### Загрузите ингредиенты в базу данных

```
sudo docker-compose exec backend python manage.py load_indredients
```

### Автор

Иван Артамонов
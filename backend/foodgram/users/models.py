from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Модель пользователя"""

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    email = models.EmailField(
        'Электронная почта',
        unique=True,
    )
    username = models.CharField(
        'Юзернейм',
        unique=True,
        max_length=255,
    )
    password = models.CharField(
        'Пароль',
        max_length=255,
    )
    first_name = models.CharField(
        'Имя',
        max_length=255,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=255,
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        constraints = (
            models.UniqueConstraint(fields=('email', 'username'),
                                    name='unique_auth'),
        )

    def __str__(self):
        return f'{self.username} {self.email}'


class Follow(models.Model):
    """Подписка на автора"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор рецепта',
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Подписка на автора'
        verbose_name_plural = 'Подписки на авторов'
        constraints = [
            models.UniqueConstraint(
                name='unique_follow',
                fields=['user', 'author'],
            ),
        ]

    def __str__(self):
        return f'Пользователь {self.user} подписан на {self.author}'

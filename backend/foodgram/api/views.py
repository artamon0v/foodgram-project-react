from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response

from api.filters import NameSearchFilter, RecipeFilter
from api.pagination import CustomPaginator
from api.permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from api.serializers import (FollowSerializer, IngredientSerializer,
                             RecipeCreateSerializer, RecipeFastSerializer,
                             RecipeReadSerializer, TagSerializer,
                             UserBaseSerializer)
from foodgram.settings import FILE_NAME
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Follow, User


class UserBaseViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = UserBaseSerializer
    pagination_class = CustomPaginator

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        page = self.paginate_queryset(queryset)
        serializer = FollowSerializer(page,
                                      many=True,
                                      context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            if user.id == author.id:
                return Response({'detail': 'Нельзя подписаться на себя'},
                                status=status.HTTP_400_BAD_REQUEST)
            if Follow.objects.filter(author=author, user=user).exists():
                return Response({'detail': 'Вы уже подписаны!'},
                                status=status.HTTP_400_BAD_REQUEST)
            Follow.objects.create(user=user, author=author)
            serializer = FollowSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        subscription = get_object_or_404(Follow, user=user, author=author)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (NameSearchFilter,)
    search_fields = ('^name',)
    pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = CustomPaginator
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter
    http_method_names = [
        m for m in viewsets.ModelViewSet.http_method_names if m not in ['put']
    ]

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def manage_object(self, request, model, model_name, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response({'errors': f'{model_name} уже существует'},
                                status=status.HTTP_400_BAD_REQUEST)
            model.objects.create(user=user, recipe=recipe)
            serializer = RecipeFastSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        instance = get_object_or_404(model, user=user, recipe=recipe)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self.manage_object(request, Favorite, 'Рецепт', pk)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self.manage_object(request, ShoppingCart, 'Список покупок', pk)

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request, **kwargs):
        ingredients = (
            IngredientInRecipe.objects
            .filter(recipe__in_shopping_cart__user=request.user)
            .values('ingredient')
            .annotate(total_amount=Sum('amount'))
            .values_list('ingredient__name', 'total_amount',
                         'ingredient__measurement_unit')
        )
        file_list = []
        [file_list.append(
            '{} - {} {}.'.format(*ingredient)) for ingredient in ingredients]
        file = HttpResponse('Cписок покупок:\n' + '\n'.join(file_list),
                            content_type='text/plain')
        file['Content-Disposition'] = (f'attachment; filename={FILE_NAME}')
        return file

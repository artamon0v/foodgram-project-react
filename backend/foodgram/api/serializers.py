from django.db import transaction
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField

from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Follow, User


class UserBaseSerializer(UserSerializer):
    '''Базовый сериализатор пользователя.'''
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name',
                  'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return not user.is_anonymous and Follow.objects.filter(
            user=user, author=obj).exists()


class IngredientSerializer(serializers.ModelSerializer):
    '''Сериализатор ингредиентов.'''
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    '''Сериализатор тегов.'''
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class RecipeFastSerializer(ModelSerializer):
    '''Сериализатор для отображения рецептов на странице подписок.'''
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(UserBaseSerializer):
    '''Сериализатор подписoк.'''
    is_subscribed = serializers.BooleanField(default=True)
    recipes = RecipeFastSerializer(many=True, read_only=True)
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True)

    class Meta:
        model = User
        fields = UserBaseSerializer.Meta.fields + ('recipes_count', 'recipes')
        read_only_fields = ('email', 'username', 'first_name', 'last_name')


class IngredientInRecipeCreateSerializer(ModelSerializer):
    '''Сериализатор для отоброжения ингредиента при создании рецепта.'''
    id = PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount', 'name', 'measurement_unit')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = instance.ingredient.id
        return data


class RecipeReadSerializer(ModelSerializer):
    '''Сериализатор получения рецепта.'''
    author = UserBaseSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeCreateSerializer(
        source='recipe_ingredients', many=True)
    image = Base64ImageField()
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return not user.is_anonymous and Favorite.objects.filter(
            user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return not user.is_anonymous and ShoppingCart.objects.filter(
            user=user, recipe=obj).exists()


class RecipeCreateSerializer(ModelSerializer):
    '''Сериализатор создания рецепта.'''
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)
    author = UserBaseSerializer(read_only=True)
    ingredients = IngredientInRecipeCreateSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'name', 'image', 'text', 'cooking_time')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tags = attrs.get('tags', [])
        ingredients = attrs.get('ingredients', [])

        if not tags:
            raise serializers.ValidationError('Нужно добавить тег.')

        if not ingredients:
            raise serializers.ValidationError('Нужно добавить ингредиент.')

        if any(ingredient['amount'] <= 0 for ingredient in ingredients):
            raise serializers.ValidationError(
                'Количество должно быть больше 0.')

        ingredient_id_list = [item.get('id')
                              for item in ingredients
                              if item.get('id') is not None]
        unique_ingredient_id_list = set(ingredient_id_list)

        if len(ingredient_id_list) != len(unique_ingredient_id_list):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальными.'
            )

        return attrs

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance, context={'request': self.context.get('request')}).data

    @transaction.atomic
    def update(self, instance, validated_data):
        if 'tags' in validated_data:
            instance.tags.set(validated_data.pop('tags'))
        if 'ingredients' in validated_data:
            ingredients_data = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def create_ingredients(self, recipe, ingredients_data):
        ingredients = []
        for ingredient_data in ingredients_data:
            ingredient = IngredientInRecipe(
                recipe=recipe,
                ingredient_id=ingredient_data['id'].id,
                amount=ingredient_data['amount']
            )
            ingredients.append(ingredient)
        IngredientInRecipe.objects.bulk_create(ingredients)

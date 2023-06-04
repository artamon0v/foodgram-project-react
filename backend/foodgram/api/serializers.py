from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer
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


class FollowSerializer(UserBaseSerializer):
    '''Сериализатор подписoк.'''
    is_subscribed = serializers.BooleanField(default=True)
    recipes = SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True)

    class Meta:
        model = User
        fields = UserBaseSerializer.Meta.fields + ('recipes_count', 'recipes')
        read_only_fields = ('email', 'username', 'first_name', 'last_name')

    def get_recipes(self, obj):
        recipes = obj.recipes.all()
        return RecipeFastSerializer(
            recipes, many=True, context=self.context).data


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


class IngredientInRecipeCreateSerializer(ModelSerializer):
    '''Сериализатор для отоброжения ингредиента при создании рецепта.'''
    id = serializers.ReadOnlyField(source='ingredient.id')
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

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Нужно добавить тег.')
        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError('Нужно добавить ингридиент.')
        if any(i['amount'] <= 0 for i in value):
            raise serializers.ValidationError(
                'Колличество должго быть больше 0')
        return value

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance, context={'request': self.context.get('request')}).data

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        for ingredient in ingredients:
            IngredientInRecipe.objects.create(recipe=recipe,
                                              ingredient=ingredient['id'],
                                              amount=ingredient['amount'])
        return recipe

    def update(self, instance, validated_data):
        if 'tags' in validated_data:
            instance.tags.set(validated_data.pop('tags'))
        if 'ingredients' in validated_data:
            instance.ingredients.clear()
            for ingredient in validated_data.pop('ingredients'):
                IngredientInRecipe.objects.update_or_create(
                    recipe=instance,
                    ingredient=ingredient['id'],
                    defaults={'amount': ingredient['amount']})
        return super().update(instance, validated_data)

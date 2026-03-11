from django.urls import path
from . import views

urlpatterns = [
    path("", views.MainListView.as_view(), name="main"),

    path("login/", views.LoginView.as_view(), name="login"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("register/otp/", views.RegisterOtpView.as_view(), name="register-otp"),
    path("logout/", views.LogoutView.as_view(), name="logout"),

    path("search", views.SearchView.as_view(), name="search"),
    path("search/", views.SearchView.as_view()),

    path("category", views.ProductListView.as_view()),
    path("category/", views.ProductListView.as_view(), name="product_list_all"),
    path("category/<int:category_id>/", views.ProductListView.as_view(), name="product_list"),
    path("product/<int:pk>/", views.ProductDetailView.as_view(), name="product_detail"),

    path("order/create/", views.OrderCreateView.as_view(), name="order-create"),
    path("order/success/<int:pk>/", views.OrderSuccessView.as_view(), name="order-success"),

    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/add/", views.CartAddView.as_view(), name="cart-add"),
    path("cart/item/<int:item_id>/update/", views.CartUpdateView.as_view(), name="cart-update"),
    path("cart/item/<int:item_id>/remove/", views.CartRemoveView.as_view(), name="cart-remove"),
    path("cart/order/", views.CartOrderView.as_view(), name="cart-order"),
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),

    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/delete/otp/", views.ProfileDeleteOtpRequestView.as_view(), name="profile-delete-otp"),
    path("profile/delete/", views.ProfileDeleteView.as_view(), name="profile-delete"),
    path("profile/orders/", views.OrderHistoryView.as_view(), name="order-history"),
    path("market/", views.MarketView.as_view()),
    path("market/<int:category_id>/", views.MarketView.as_view(), name="market"),
    path("wishlist/toggle/", views.WishlistToggleView.as_view(), name="wishlist-toggle"),
    path("survey/", views.SurveyView.as_view(), name="survey"),
]

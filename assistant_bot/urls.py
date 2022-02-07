from django.urls import path
from django.contrib.auth.views import LogoutView

from .views import HomePage, CustomLoginView, RegisterPage, AddressBookCreate, AddressBookView, delete_addressbook,\
    AddressBookUpdate, AddressBookDetail, NoteBookCreate, NoteBookDetail, NoteBookView, NoteBookUpdate, \
    delete_notebook, show_world_news, show_finance_news, show_sport_news, show_entertainment_news, show_tech_news,\
    show_weather, currency_converter, file_upload_view, show_files, reference, delete_file


url_patterns = [
    path('', HomePage.as_view(), name='homepage'),

    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', RegisterPage.as_view(), name='register'),

    path('add-contact/', AddressBookCreate.as_view(), name='addressbook'),
    path('view-contacts/', AddressBookView.as_view(), name='contacts'),
    path('task-delete/<int:pk>', delete_addressbook, name='delete'),
    path('task-update/<int:pk>', AddressBookUpdate.as_view(), name='update'),
    path('contact-view/<int:pk>', AddressBookDetail.as_view(), name='contact'),

    path('note-add/', NoteBookCreate.as_view(), name='note_create'),
    path('note-view/<int:pk>', NoteBookDetail.as_view(), name='note'),
    path('view-notes/', NoteBookView.as_view(), name='notes'),
    path('note-update/<int:pk>', NoteBookUpdate.as_view(), name='note-update'),
    path('delete-note/<int:pk>', delete_notebook, name='delete_note'),

    path('news/', show_world_news,  name='news'),
    path('finance/', show_finance_news, name='finance'),
    path('sport/', show_sport_news, name='sport'),
    path('entertainment/', show_entertainment_news, name='entertainment'),
    path('techcrunch/', show_tech_news, name='techcrunch'),
    path('weather/', show_weather, name='weather'),
    path('currency/', currency_converter, name='currency'),

    path('files/', file_upload_view, name='files'),#
    path('show-files/<slug:ext>', show_files, name='show-files'),#

    path('reference/', reference, name='reference'),
    path('delete-file/<str:ext>', delete_file, name='delete-file'),#
]

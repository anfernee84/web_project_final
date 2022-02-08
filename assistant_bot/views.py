from django.shortcuts import render, redirect
from .models import AddressBook, NoteBook, GetListFile
from django.urls import reverse_lazy
from django.db.models import Q
from .forms import AddAddressBook
from django.views.generic import TemplateView, CreateView, ListView, UpdateView, DetailView

from django.contrib.auth.views import LoginView, login_required, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages

from django.core.files.storage import FileSystemStorage

from django.http import HttpResponseRedirect, HttpResponse

from newsapi import NewsApiClient

import json

import requests

import urllib.request
import urllib.parse

import datetime

from re import split

from calendar import monthrange

from pycountry import countries

import os

from distutils import file_util

from idna import valid_contextj


class CustomLoginView(LoginView):
    template_name = 'login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('homepage')

    def form_invalid(self, form):
        messages.success(self.request, 'Incorrect password or login!')
        return super(CustomLoginView, self).form_invalid(form)


class RegisterPage(FormView):
    template_name = 'register.html'
    form_class = UserCreationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save()
        if user is not None:
            login(self.request, user)
        return super(RegisterPage, self).form_valid(form)

    def form_invalid(self, form):
        messages.success(self.request, 'Your password is too common or is incorrect!')
        return super(RegisterPage, self).form_invalid(form)


class HomePage(LoginRequiredMixin, TemplateView):
    template_name = 'homepage.html'


class AddressBookCreate(CreateView):
    model = AddressBook
    form_class = AddAddressBook
    template_name = 'addressbook_add.html'
    success_url = reverse_lazy('contacts')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(AddressBookCreate, self).form_valid(form)


class AddressBookView(LoginRequiredMixin, ListView):
    model = AddressBook
    template_name = 'addressbook_listview.html'
    context_object_name = 'contacts'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(AddressBookView, self).get_context_data(**kwargs)
        context['all_contacts'] = AddressBook.objects.filter(user=self.request.user).all()
        context['contacts'] = context['contacts'].filter(user=self.request.user)

        today_date = datetime.date.today()

        search_input = self.request.GET.get('search-area')
        b_day = self.request.GET.get('b-day')
        all_input = self.request.GET.get('all')
        if search_input:
            context['contacts'] = context['contacts'].filter(
                Q(name__icontains=search_input) | Q(surname__icontains=search_input) | Q(phone__icontains=search_input))
            context['is_empty'] = True
            return context

        if b_day:
            if today_date.day + 7 <= monthrange(today_date.year, today_date.month)[1]:
                context['contacts'] = context['contacts'].filter(birthday__month=today_date.month,
                                                                 birthday__day__range=(
                                                                     today_date.day, today_date.day + 7))
            elif today_date.day + 7 > monthrange(today_date.year, today_date.month)[1]:
                diff_days = today_date.day + 7 - monthrange(today_date.year, today_date.month)[1]
                context['contacts'] = context['contacts'].filter(Q(birthday__month=today_date.month + 1,
                                                                 birthday__day__range=(
                                                                     1, diff_days))|Q(birthday__month=today_date.month, birthday__day__range=(today_date.day, today_date.day+7)))

        if all_input is not None:
            context['contacts'] = AddressBook.objects.filter(user=self.request.user)

        if context['contacts']:
            context['is_empty'] = '0'

        return context


@login_required
def delete_addressbook(response, pk):
    model = AddressBook.objects.filter(id=pk)
    model.delete()
    return redirect('contacts')


class AddressBookUpdate(LoginRequiredMixin, UpdateView):
    model = AddressBook
    template_name = 'addressbook_update.html'
    context_object_name = 'contact'
    form_class = AddAddressBook
    success_url = reverse_lazy('contacts')


class AddressBookDetail(LoginRequiredMixin, DetailView):
    model = AddressBook
    template_name = 'addressbook_detailview.html'
    context_object_name = 'contact'


class NoteBookCreate(CreateView):
    model = NoteBook

    fields = ['title', 'description', 'tags']
    template_name = 'notebook_add.html'
    success_url = reverse_lazy('notes')

    def form_valid(self, form):
        tags = form.instance.tags
        form.instance.user = self.request.user
        if tags:
            form.instance.tags = list(set(split(r'[,;+= ]', tags[0])))
        return super(NoteBookCreate, self).form_valid(form)


class NoteBookDetail(LoginRequiredMixin, DetailView):
    model = NoteBook
    template_name = 'notebook_detail_view.html'
    context_object_name = 'note'


class NoteBookUpdate(LoginRequiredMixin, UpdateView):
    model = NoteBook
    template_name = 'notebook_update.html'
    fields = ['title', 'description', 'tags']
    success_url = reverse_lazy('notes')


class NoteBookView(LoginRequiredMixin, ListView):
    model = NoteBook
    template_name = 'notebook_listview.html'
    context_object_name = 'notes'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(NoteBookView, self).get_context_data(**kwargs)
        context['all_notes'] = NoteBook.objects.filter(user=self.request.user).all()
        context['notes'] = context['notes'].filter(user=self.request.user)

        tag_set = set()
        search_input = self.request.GET.get('search-area')
        filter_tags = get_tags_from_request(self.request.GET, self.request.user)

        if filter_tags:
            context['notes'] = context['notes'].filter(tags__overlap=filter_tags)

        if search_input:
            context['notes'] = context['notes'].filter(title__icontains=search_input)

        for tag_item in NoteBook.objects.filter(user=self.request.user).values_list('tags', flat=True).order_by('tags'):
            if tag_item:
                for tag in tag_item:
                    tag_set.add(tag)
        context['filter_tags'] = tag_set

        if context['notes']:
            context['notes_exist'] = True

        return context


def get_tags_from_request(get_request, user):

    all_tags = NoteBook.objects.filter(user=user).values_list('tags', flat=True)
    searched_tags = []
    for tag_item in all_tags:
        if tag_item:
            for tag in tag_item:
                if get_request.get(tag):
                    searched_tags.append(tag)
    return searched_tags


@login_required
def delete_notebook(response, pk):
    model = NoteBook.objects.filter(id=pk)
    model.delete()
    tag_set = set()
    for tag_item in NoteBook.objects.values_list('tags', flat=True).order_by('tags'):
        if tag_item:
            for tag in tag_item:
                tag_set.add(tag)
    return redirect('notes')


@login_required
def show_world_news(request):
    newsapi = NewsApiClient(api_key='92ee8fd958374204ada73045c7fe5936')
    top = newsapi.get_top_headlines(sources='bbc-news')

    content = top['articles']
    desc = []
    news = []
    img = []
    url = []

    for i in range(len(content)):
        text = content[i]
        news.append(text['title'])
        desc.append(text['description'])
        img.append(text['urlToImage'])
        url.append(text['url'])
    mylist = zip(news, desc, img, url)

    user_location = json.loads(urllib.request.urlopen('http://ipinfo.io/json').read())
    weather_url = urllib.request.urlopen(
        f"https://api.openweathermap.org/"
        f"data/2.5/weather?q={urllib.parse.quote(user_location['city'])}&appid=206c04ecd30711b37b3e460efd0e40d7"
    ).read()
    weather_data = json.loads(weather_url)
    data = {
        'name': weather_data['name'],
        'temp_c': (weather_data['main']['temp'] - 273.15).__round__(1),
        'temp_f': ((weather_data['main']['temp'] - 273.15) * 9 / 5 + 32).__round__(1)}

    return render(request=request, template_name='news_page.html', context={'mylist': mylist, 'data': data})


@login_required
def show_finance_news(request):
    newsapi = NewsApiClient(api_key='92ee8fd958374204ada73045c7fe5936')
    top = newsapi.get_top_headlines(sources='business-insider')

    content = top['articles']
    desc = []
    news = []
    img = []
    url = []

    for i in range(len(content)):
        text = content[i]
        news.append(text['title'])
        desc.append(text['description'])
        img.append(text['urlToImage'])
        url.append(text['url'])
    mylist = zip(news, desc, img, url)

    user_location = json.loads(urllib.request.urlopen('http://ipinfo.io/json').read())
    weather_url = urllib.request.urlopen(
        f"https://api.openweathermap.org/"
        f"data/2.5/weather?q={urllib.parse.quote(user_location['city'])}&appid=206c04ecd30711b37b3e460efd0e40d7"
    ).read()
    weather_data = json.loads(weather_url)
    data = {
        'name': weather_data['name'],
        'temp_c': (weather_data['main']['temp'] - 273.15).__round__(1),
        'temp_f': ((weather_data['main']['temp'] - 273.15) * 9 / 5 + 32).__round__(1)}

    return render(request=request, template_name='finance_page.html', context={'mylist': mylist, 'data': data})


@login_required()
def show_sport_news(request):
    newsapi = NewsApiClient(api_key='92ee8fd958374204ada73045c7fe5936')
    top = newsapi.get_top_headlines(sources='bbc-sport')

    content = top['articles']
    desc = []
    news = []
    img = []
    url = []

    for i in range(len(content)):
        text = content[i]
        news.append(text['title'])
        desc.append(text['description'])
        img.append(text['urlToImage'])
        url.append(text['url'])
    mylist = zip(news, desc, img, url)

    user_location = json.loads(urllib.request.urlopen('http://ipinfo.io/json').read())
    weather_url = urllib.request.urlopen(
        f"https://api.openweathermap.org/"
        f"data/2.5/weather?q={urllib.parse.quote(user_location['city'])}&appid=206c04ecd30711b37b3e460efd0e40d7"
    ).read()
    weather_data = json.loads(weather_url)
    data = {
        'name': weather_data['name'],
        'temp_c': (weather_data['main']['temp'] - 273.15).__round__(1),
        'temp_f': ((weather_data['main']['temp'] - 273.15) * 9 / 5 + 32).__round__(1)}

    return render(request=request, template_name='sport_page.html', context={'mylist': mylist, 'data': data})


@login_required()
def show_entertainment_news(request):
    newsapi = NewsApiClient(api_key='92ee8fd958374204ada73045c7fe5936')
    top = newsapi.get_top_headlines(sources='buzzfeed')

    content = top['articles']
    desc = []
    news = []
    img = []
    url = []

    for i in range(len(content)):
        text = content[i]
        news.append(text['title'])
        desc.append(text['description'])
        img.append(text['urlToImage'])
        url.append(text['url'])
    mylist = zip(news, desc, img, url)

    user_location = json.loads(urllib.request.urlopen('http://ipinfo.io/json').read())
    weather_url = urllib.request.urlopen(
        f"https://api.openweathermap.org/"
        f"data/2.5/weather?q={urllib.parse.quote(user_location['city'])}&appid=206c04ecd30711b37b3e460efd0e40d7"
    ).read()
    weather_data = json.loads(weather_url)
    data = {
        'name': weather_data['name'],
        'temp_c': (weather_data['main']['temp'] - 273.15).__round__(1),
        'temp_f': ((weather_data['main']['temp'] - 273.15) * 9 / 5 + 32).__round__(1)}

    return render(request=request, template_name='entertainment_page.html', context={'mylist': mylist, 'data': data})


@login_required
def show_tech_news(request):
    newsapi = NewsApiClient(api_key='92ee8fd958374204ada73045c7fe5936')
    top = newsapi.get_top_headlines(sources='techcrunch')

    content = top['articles']
    desc = []
    news = []
    img = []
    url = []

    for i in range(len(content)):
        text = content[i]
        news.append(text['title'])
        desc.append(text['description'])
        img.append(text['urlToImage'])
        url.append(text['url'])
    mylist = zip(news, desc, img, url)

    user_location = json.loads(urllib.request.urlopen('http://ipinfo.io/json').read())
    weather_url = urllib.request.urlopen(
        f"https://api.openweathermap.org/"
        f"data/2.5/weather?q={urllib.parse.quote(user_location['city'])}&appid=206c04ecd30711b37b3e460efd0e40d7"
    ).read()
    weather_data = json.loads(weather_url)
    data = {
        'name': weather_data['name'],
        'temp_c': (weather_data['main']['temp'] - 273.15).__round__(1),
        'temp_f': ((weather_data['main']['temp'] - 273.15) * 9 / 5 + 32).__round__(1)}

    return render(request=request, template_name='tech_page.html', context={'mylist': mylist, 'data': data})


@login_required()
def show_weather(request):
    user_location = json.loads(urllib.request.urlopen('http://ipinfo.io/json').read())
    weather_url = urllib.request.urlopen(
        f"https://api.openweathermap.org/"
        f"data/2.5/weather?q={urllib.parse.quote(user_location['city'])}&appid=206c04ecd30711b37b3e460efd0e40d7"
    ).read()
    weather_data = json.loads(weather_url)
    data = {
        'name': weather_data['name'],
        'country': countries.get(alpha_2=weather_data['sys']['country']).name,
        'temp_c': (weather_data['main']['temp'] - 273.15).__round__(1),
        'temp_f': ((weather_data['main']['temp'] - 273.15) * 9 / 5 + 32).__round__(1),
        'clouds': weather_data['clouds']['all'],
        'wind_kmh': (weather_data['wind']['speed'] * 3.6).__round__(1),
        'wind_mh': (weather_data['wind']['speed'] * 2.237).__round__(1),
        'visibility_km': (weather_data['visibility'] / 1000).__round__(1),
        'visibility_m': (weather_data['visibility'] / 1609).__round__(1),
        'pressure': weather_data['main']['pressure'],
        'humidity': weather_data['main']['humidity'],
        'dt': datetime.datetime.now().date().ctime().replace(' 00:00:00', ',')
    }
    if request.method == 'POST':
        weather_url = urllib.request.urlopen(
            f"https://api.openweathermap.org/"
            f"data/2.5/weather?q={urllib.parse.quote(request.POST['location'])}&appid=206c04ecd30711b37b3e460efd0e40d7"
        ).read()
        weather_data = json.loads(weather_url)
        data = {
            'name': weather_data['name'],
            'country': countries.get(alpha_2=weather_data['sys']['country']).name,
            'temp_c': (weather_data['main']['temp'] - 273.15).__round__(1),
            'temp_f': ((weather_data['main']['temp'] - 273.15) * 9 / 5 + 32).__round__(1),
            'clouds': weather_data['clouds']['all'],
            'wind_kmh': (weather_data['wind']['speed'] * 3.6).__round__(1),
            'wind_mh': (weather_data['wind']['speed'] * 2.237).__round__(1),
            'visibility_km': (weather_data['visibility'] / 1000).__round__(1),
            'visibility_m': (weather_data['visibility'] / 1609).__round__(1),
            'pressure': weather_data['main']['pressure'],
            'humidity': weather_data['main']['humidity'],
            'dt': datetime.datetime.now().date().ctime().replace(' 00:00:00', ',')
        }
        return render(request=request, template_name='weather_page.html', context={'data': data})
    return render(request=request, template_name='weather_page.html', context={'data': data})


@login_required
def currency_converter(request):
    response = requests.get('https://api.exchangerate.host/latest')
    result = response.json()
    data = {
        'aud': result['rates']['AUD'].__round__(2),
        'bgn': result['rates']['BGN'].__round__(2),
        'brl': result['rates']['BRL'].__round__(2),
        'cad': result['rates']['CAD'].__round__(2),
        'chf': result['rates']['CHF'].__round__(2),
        'cny': result['rates']['CNY'].__round__(2),
        'czk': result['rates']['CZK'].__round__(2),
        'dkk': result['rates']['DKK'].__round__(2),
        'eur': result['rates']['EUR'].__round__(2),
        'gbp': result['rates']['GBP'].__round__(2),
        'hkd': result['rates']['HKD'].__round__(2),
        'hrk': result['rates']['HRK'].__round__(2),
        'huf': result['rates']['HUF'].__round__(2),
        'idr': result['rates']['IDR'].__round__(2),
        'ils': result['rates']['ILS'].__round__(2),
        'inr': result['rates']['INR'].__round__(2),
        'isk': result['rates']['ISK'].__round__(2),
        'jpy': result['rates']['JPY'].__round__(2),
        'krw': result['rates']['KRW'].__round__(2),
        'mxn': result['rates']['MXN'].__round__(2),
        'myr': result['rates']['MYR'].__round__(2),
        'nok': result['rates']['NOK'].__round__(2),
        'nzd': result['rates']['NZD'].__round__(2),
        'php': result['rates']['PHP'].__round__(2),
        'pln': result['rates']['PLN'].__round__(2),
        'ron': result['rates']['RON'].__round__(2),
        'rub': result['rates']['RUB'].__round__(2),
        'sek': result['rates']['SEK'].__round__(2),
        'sgd': result['rates']['SGD'].__round__(2),
        'thb': result['rates']['THB'].__round__(2),
        'try': result['rates']['TRY'].__round__(2),
        'uah': result['rates']['UAH'].__round__(2),
        'usd': result['rates']['USD'].__round__(2),
        'zar': result['rates']['ZAR'].__round__(2),
    }

    if request.method == 'POST':
        exchange = (((1 / result['rates'][request.POST.get('currency_first')]) *
                     result['rates'][request.POST.get('currency_second')]) *
                    int(request.POST.get('amount'))).__round__(3)
        exchange_out = f"{request.POST.get('amount')} {request.POST.get('currency_first')} = " \
                       f"{exchange} {request.POST.get('currency_second')}"
        return render(request=request, template_name='currency.html', context={
            'data': data, 'exchange_out': exchange_out
        })
    return render(request=request, template_name='currency.html', context={'data': data})



def file_filter(*args):
    EXTENDS = {
        'IMAGES': ['png', 'jpeg', 'jpg', 'bmp'],
        'DOCUMENTS': ['doc', 'docx', 'xls', 'xlsx', 'pdf'],
        'VIDEO': ['avi', 'mkv', 'mp4'],
        'MUSIC': ['mp3', 'vaw'],
        # 'OTHER': []
    }
    FILE_LIST_BY_EXT = {
        'IMAGES': [],
        'DOCUMENTS': [],
        'VIDEO': [],
        'MUSIC': [],
        'OTHER': [],
        'ALL': []
    }
    path = "media/" + str(*args)
    if os.path.isdir(path):
        file_list = os.listdir(path)
        for file in file_list:
            ext_flag = False
            l_ext = file.split('.')[-1]
            for EXT in EXTENDS:
                if l_ext in EXTENDS[EXT]:
                    ext_flag = EXT
            if ext_flag:
                FILE_LIST_BY_EXT[ext_flag].append(file)
            else:
                FILE_LIST_BY_EXT['OTHER'].append(file)
            FILE_LIST_BY_EXT['ALL'].append(file)
    else:
        pass
    return FILE_LIST_BY_EXT


@login_required
def show_files(request, ext):
    user_id = request.user.id
    file_list = file_filter(user_id)
    return render(request, 'show_files.html', {'file_list': file_list[ext], "user_id": user_id})


@login_required
def file_upload_view(request):
    success = False
    file_list = False
    path = "media/"
    user_id = request.user.id  # Get user_id from request
    if request.method == 'POST':
        uploaded_file = request.FILES['document'] if "document" in request.FILES else False
        if uploaded_file:
            fs = FileSystemStorage(location=str(str(path) + str(user_id)))
            fs.save(uploaded_file.name, uploaded_file)
            success = "File uploaded successfully"
        else:
            pass
    file_list = file_filter(request)
    return render(request, 'files.html', {'success': success, 'file_list': file_list.keys()})


@login_required
def delete_file(request, ext):
    user_id = request.user.id
    print(user_id)
    path = f"media/{str(user_id)}/{str(ext)}"
    return_to_refer = request.META.get('HTTP_REFERER')
    print(request.META.get('HTTP_REFERER'))
    os.remove(path)
    file_list = file_filter()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def reference(request):
    return render(request=request, template_name='reference.html')

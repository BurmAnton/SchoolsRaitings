from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy

class MyAdminSite(AdminSite):
    # Text to put at the end of each page's <title>.
    site_title = gettext_lazy('АИС «Оценка качества работы руководителя ОО»')

    # Text to put in each page's <h1> (and above login form).
    site_header = gettext_lazy('АИС «Оценка качества работы руководителя ОО»')

    # Text to put at the top of the admin index page.
    index_title = gettext_lazy('АИС «Оценка качества работы руководителя ОО»')

admin_site = MyAdminSite()
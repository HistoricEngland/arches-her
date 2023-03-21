from arches.app.views.plugin import PluginView
from django.conf.urls import include, url
from django.conf import settings
from django.conf.urls.static import static
from arches_her.views.file_template import FileTemplateView
from arches_her.views.index import IndexView
from django.views.generic import RedirectView
from arches_her.views.resource import ResourceDescriptors
from arches_her.views.active_consultations import ActiveConsultationsView
from arches.app.views import main
from arches.app.views.user import UserManagerView
from arches.app.views.auth import PasswordResetView

uuid_regex = settings.UUID_REGEX

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='root'),
    url(r'^'+settings.APP_PATHNAME+'/$', IndexView.as_view(), name='consultations-root'),
    url(r'^index.htm', IndexView.as_view(), name='home'),
    url(r'^'+settings.APP_PATHNAME+'/index.htm', IndexView.as_view(), name='consultations-home'),
    url(r'^'+settings.APP_PATHNAME+'/', include('arches.urls')),
    url(r'^plugins/active-consultations$', RedirectView.as_view(url='/'+settings.APP_PATHNAME+'/plugins/active-consultations')),
    url(r'^resource/descriptors/(?P<resourceid>%s|())$' % uuid_regex, ResourceDescriptors.as_view(), name="resource_descriptors"),
    url(r'^'+settings.APP_PATHNAME+'/index.htm', IndexView.as_view(), name='home'),
    url(
    r"^password_reset/$",
    PasswordResetView.as_view(html_email_template_name="registration/password_reset_html_email.html",extra_email_context={'app_title':settings.APP_TITLE,'contact_website':settings.CONTACT_WEBSITE,'contact_email':settings.CONTACT_EMAIL}),
    name="password_reset",),
    url(r'^', include('arches.urls')),
    url(r'^'+settings.APP_PATHNAME+'/user$', UserManagerView.as_view(), name="user_profile_manager"),
    url(r'^filetemplate', FileTemplateView.as_view(), name='filetemplate'),
    url(r'^'+settings.APP_PATHNAME+'/plugins/active-consultations', PluginView.as_view(), name='active-consultations'),
    url(r'^activeconsultations', ActiveConsultationsView.as_view(),
        name='activeconsultations'),
    url(r'^'+settings.APP_PATHNAME+'/plugins/consultation-workflow', PluginView.as_view(), name='consultation-workflow'),
    url(r'^'+settings.APP_PATHNAME+'/plugins/application-area', PluginView.as_view(), name='application-area'),
    url(r'^'+settings.APP_PATHNAME+'/plugins/site-visit', PluginView.as_view(), name='site-visit'),
    url(r'^'+settings.APP_PATHNAME+'/plugins/correspondence-workflow', PluginView.as_view(), name='correspondence-workflow'),
    url(r'^'+settings.APP_PATHNAME+'/plugins/communication-workflow', PluginView.as_view(), name='communication-workflow'),
    url(r'^'+settings.APP_PATHNAME+'/plugins/init-workflow', PluginView.as_view(), name='init-workflow')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

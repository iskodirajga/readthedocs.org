import datetime

import stripe
from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext_lazy as _
from vanilla import CreateView, DeleteView, UpdateView, DetailView

from readthedocs.core.mixins import LoginRequiredMixin
from readthedocs.projects.models import Project
from readthedocs.payments.mixins import StripeMixin

from .forms import GoldSubscriptionForm, GoldProjectForm
from .models import GoldUser

stripe.api_key = settings.STRIPE_SECRET


class GoldSubscriptionView(SuccessMessageMixin, StripeMixin, LoginRequiredMixin):

    model = GoldUser
    form_class = GoldSubscriptionForm

    def get_object(self):
        try:
            return self.get_queryset().get(user=self.request.user)
        except self.model.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        context = (super(GoldSubscriptionView, self)
                   .get_context_data(**kwargs))
        context['stripe_publishable'] = settings.STRIPE_PUBLISHABLE
        return context

    def get_form(self, data=None, files=None, **kwargs):
        """Pass in copy of POST data to avoid read only QueryDicts"""
        kwargs['customer'] = self.request.user
        return super(GoldSubscriptionView, self).get_form(data, files, **kwargs)

    def get_success_url(self, **kwargs):
        return reverse_lazy('gold_detail')

    def get_template_names(self):
        return ('gold/subscription{0}.html'
                .format(self.template_name_suffix))


# Subscription Views
class DetailGoldSubscription(GoldSubscriptionView, DetailView):

    def get(self, request, *args, **kwargs):
        resp = super(DetailGoldSubscription, self).get(request, *args, **kwargs)
        if self.object is None:
            return HttpResponseRedirect(reverse('gold_subscription'))
        return resp


class UpdateGoldSubscription(GoldSubscriptionView, UpdateView):
    success_message = _('Your subscription has been updated')


class DeleteGoldSubscription(GoldSubscriptionView, DeleteView):

    """Delete Gold subscription view

    On object deletion, the corresponding Stripe customer is deleted as well.
    Deletion is triggered on subscription deletion, to ensure the subscription
    is synced with Stripe.
    """

    success_message = _('Your subscription has been cancelled')

    def post(self, request, *args, **kwargs):
        """Add success message to delete post"""
        resp = super(SuccessMessageMixin, self).post(request, *args, **kwargs)
        success_message = self.get_success_message({})
        if success_message:
            messages.success(self.request, success_message)
        return resp


@login_required
def projects(request):
    gold_user = get_object_or_404(GoldUser, user=request.user)
    gold_projects = gold_user.projects.all()

    if request.method == 'POST':
        form = GoldProjectForm(data=request.POST, user=gold_user, projects=gold_projects)
        if form.is_valid():
            to_add = Project.objects.get(slug=form.cleaned_data['project'])
            gold_user.projects.add(to_add)
            return HttpResponseRedirect(reverse('gold_projects'))
    else:
        form = GoldProjectForm()

    return render_to_response(
        'gold/projects.html',
        {
            'form': form,
            'gold_user': gold_user,
            'publishable': settings.STRIPE_PUBLISHABLE,
            'user': request.user,
            'projects': gold_projects
        },
        context_instance=RequestContext(request)
    )


@login_required
def projects_remove(request, project_slug):
    gold_user = get_object_or_404(GoldUser, user=request.user)
    project = get_object_or_404(Project.objects.all(), slug=project_slug)
    gold_user.projects.remove(project)
    return HttpResponseRedirect(reverse('gold_projects'))

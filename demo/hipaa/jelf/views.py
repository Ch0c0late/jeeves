"""Views for HIPAA case study.

    :synopsis: Code for displaying HIPAA demo pages.

.. moduleauthor:: Ariel Jacobs <arielj@mit.edu>
.. moduleauthor:: Jean Yang <jeanyang@csail.mit.edu>
"""
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect #, HttpResponse
#from django.contrib.auth.models import User
#from django.views import generic
from datetime import date
#import urllib
#import random

from jelf.models import Diagnosis, Individual, CoveredEntity, UserProfile, \
    Transaction, Treatment

from sourcetrans.macro_module import macros, jeeves
import JeevesLib

# TODO: Figure out what this is used for and write a comment about it.
INFORMATION_SET = {
      "preview" : "5 regarding Joe McGray"
    , "treatments" : [
          {"patient" : {"name" : "Joe McGray", "ein" : 5}
         , "service" : "ADA:D4211"
         , "date_performed" : date(2012, 6, 26)
		     , "prescribing_entity" : {"name" : "Cooper Base Dental", "ein" : 5}
         , "performing_entity" : {"name" : "Cooper Base Dental", "ein" : 5}}
        , {"patient" : {"name" : "Joe McGray", "ein" : 5}
         , "service" : "D7287"
			   , "date_performed" : date(2013, 1, 3)
         , "prescribing_entity" : {"name" : "Beautiful Smile", "ein" : 23}
         , "performing_entity" : {"name" : "Mary Orman, DDS", "ein" : 942}}]
    , "diagnoses" : [
          {"patient" : {"name" : "Joe McGray", "ein" : 5}
         , "Manifestation" : "B01.0"
         , "DateRecognized" : date(2013, 2, 1)
         , "RecognizingEntity" : {"name" : "Solomon Health", "ein" : 7}
         , "Diagnosis" : "Negative"}
        , {"Patient" : {"name" : "Joe McGray", "ein" : 5}
          , "Manifestation" : "T84.012"
          , "DateRecognized" : date(2013, 10, 17)
          , "RecognizingEntity" : {"name" : "Dr. Wragley Medical Center"
                                 , "ein" : 130}
          , "Diagnosis" : "Positive"}]
    , "hospitalVisits" : [
        {"Patient" : {"name" : "Joe McGray", "ein" : 5}
       , "DateAdmitted" : date(2014, 5, 25)
       , "Location" : "113B"
       , "Condition" : "Recovering"
       , "ReligiousAffiliation" : "None"}]}

def register_account(request):
    """Account registration.
    """
    if request.user.is_authenticated():
        return HttpResponseRedirect("index")

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            print user.username
            print request.POST.get('email', '')
            print request.POST.get('name', '')
            user.save()

            profiletype = request.POST.get('profiletype', '')
            UserProfile.objects.create(
                  username=user.username
                , email=request.POST.get('email', '')
                , name=request.POST.get('name', '')
                , profiletype=int(profiletype))
            user = authenticate(username=request.POST['username'],
            password=request.POST['password1'])
            login(request, user)
            return HttpResponseRedirect("index")
    else:
        form = UserCreationForm()

    return render_to_response("registration/account.html"
        , RequestContext(request,
		        {'form' : form
           , 'which_page' : "register"}))

@jeeves
def add_to_context(context_dict, request, template_name, profile, concretize):
    """Adds relevant arguments to the context.
    """
    template_name = concretize(template_name)
    context_dict['concretize'] = concretize
    context_dict['profile'] = profile
    context_dict['is_logged_in'] = (request.user and
                                    request.user.is_authenticated() and
                                    (not request.user.is_anonymous()))

def request_wrapper(view_fn):
    """Wraps requests by setting the current viewing context and fetching the
    profile associated with that context.
    """
    def real_view_fn(request, *args, **kwargs):
        try:
            profile = UserProfile.objects.get(username=request.user.username)
            ans = view_fn(request, profile, *args, **kwargs)
            template_name = ans[0]
            context_dict = ans[1]

            if template_name == "redirect":
                path = context_dict
                return HttpResponseRedirect(JeevesLib.concretize(profile, path))

            concretizeState = \
                JeevesLib.jeevesState.policyenv.getNewSolverState(profile)
            def concretize(val):
                return concretizeState.concretizeExp(
                    val, JeevesLib.jeevesState.pathenv.getEnv())
            add_to_context(
                context_dict, request, template_name, profile, concretize)
            return render_to_response(
                template_name, RequestContext(request, context_dict))
        except Exception:
            import traceback
            traceback.print_exc()
            raise
    real_view_fn.__name__ = view_fn.__name__
    return real_view_fn

@login_required
@request_wrapper
@jeeves
def index(request, profile):
    """The main page shows patients and entities.
    """
    patients = Individual.objects.all()
    entities = CoveredEntity.objects.all()

    # TODO: Filter out ones you can't see?

    data = {"patients": patients
          , "entities": entities
          , 'name': profile.name}
    return ("index.html", data)

@request_wrapper
@jeeves
def about_view(request, user):
    """About the system.
    """
    # TODO: This doesn't work.
    return ("about.html"
            , {'which_page' : "about"})

@login_required
@request_wrapper
@jeeves
def profile_view(request, profile):
    """Displaying and updating profiles.
    """
    if profile == None:
        profile = UserProfile(user=request.user)

    if request.method == 'POST':
        profile.name = request.POST.get('name', '')
        profile.email = request.POST.get('email', '')
        profile.save()

    return ("profile.html", {
          "profile": profile
        , "which_page": "profile"})

@login_required
@request_wrapper
@jeeves
def users_view(request, profile):
    """Viewing all users.
    """
    # TODO: Have a better mechanism than this for letting someone know they
    # can't see something.
    if profile.profiletype != 3:
        return ("redirect", "/index")

    user_profiles = UserProfile.objects.all()

    if request.method == 'POST':
        for profile in user_profiles:
            query_param_name = 'level-' + profile.username
            level = request.POST.get(query_param_name, '')
            if level in ['normal', 'pc', 'chair']:
                profile.level = level
                profile.save()

    return ("users_view.html", {
        'user_profiles': user_profiles,
        'which_page' : "users"
    })

@login_required
@request_wrapper
@jeeves
def treatments_view(request, profile, patient):
    """Treatments.
    """
    p = Individual.objects.get(jeeves_id=patient)
    treatments = Treatment.objects.filter(patient=p)
    return ("treatments.html"
        , {"first_name" : p.FirstName
         , "last_name" : p.LastName
         , "treatments" : treatments})

@login_required
@request_wrapper
@jeeves
def diagnoses_view(request, profile, patient):
    """Diagnoses.
    """
    p = Individual.objects.get(jeeves_id=patient)
    newDiagnoses = Diagnosis.objects.filter(Patient=p)
    diagnoses = [
         {"Manifestation" : "A38.8"
        , "DateRecognized" : date(2012, 10, 17)
        , "RecognizingEntity" : {"Name" : "Solomon Health", "ID" : 7}
        , "Diagnosis" : "Negative"}
      , {"Manifestation" : "E54"
        , "DateRecognized" : date(2012, 11, 24)
        , "RecognizingEntity" : {"Name" : "Cragley Medical National", "ID" : 98}
        , "Diagnosis" : "Negative"}
      , {"Manifestation" : "B01.0"
        , "DateRecognized" : date(2013, 2, 1)
        , "RecognizingEntity" : {"Name" : "Southwest Hospital", "ID" : 1}
        , "Diagnosis" : "Negative"}
      , {"Manifestation" : "T84.012"
        , "DateRecognized" : date(2013, 10, 17)
        , "RecognizingEntity" : {"Name" : "Dr. Wragley Medical Center"
                                , "ID" : 130}
      , "Diagnosis" : "Positive"}]
    return ("diagnoses.html"
            , {"first_name" : p.FirstName
             , "last_name" : p.LastName
             , "diagnoses" : newDiagnoses})

@login_required
@request_wrapper
@jeeves
def info_view(request, profile, patient):
    """Viewing information about an individual.
    """
    p = Individual.objects.get(jeeves_id=patient)
    dataset = []
    dataset.append(("Sex", p.Sex, False))
    return ("info.html"
            , {"patient": p
             , "dataset": dataset})

@login_required
@request_wrapper
@jeeves
def directory_view(request, profile, entity):
    """Viewing covered entities.
    """
    entity = CoveredEntity.objects.get(ein=entity)
    visits = entity.Patients.filter(date_released=None)

    oldVisits = [
           {"Patient" : {"name" : "Joe McGray", "ein" : 5}
          , "DateAdmitted" : date(2014, 5, 25)
          , "Location" : "113B"
          , "Condition" : "Recovering"
          , "ReligiousAffiliation" : "None"}
        , {"Patient" : {"name" : "Briann Terack", "ein" : 52}
          , "DateAdmitted" : date(2014, 3, 30)
          , "Location" : "416"
          , "Condition" : "Severe"
          , "ReligiousAffiliation" : "Catholic"}
        , {"Patient" : {"name" : "Henry Bion", "ein" : 95}
          , "DateAdmitted" : date(2014, 5, 12)
          , "Location" : "134K"
          , "Condition" : "Stable"
          , "ReligiousAffiliation" : "Christian"}
        , {"Patient" : {"name" : "Gill Hansen", "ein" : 13}
          , "DateAdmitted" : date(2014, 5, 19)
          , "Location" : "228"
          , "Condition" : "Unknown"
          , "ReligiousAffiliation" : "Christian"}]
    return ("directory.html"
            , {"entity":entity, "visits":visits})

@login_required
@request_wrapper
@jeeves
def transactions_view(request, profile, entity):
    """
    Viewing transactions.
    """
    entity = CoveredEntity.objects.get(ein=entity)
    transactions = Transaction.objects.filter(FirstParty=entity)
    other_transactions = Transaction.objects.filter(SecondParty=entity)
    return ("transactions.html"
            , {"entity": entity
             , "transactions":transactions
             , "other_transactions": other_transactions})

@login_required
@request_wrapper
@jeeves
def associates_view(request, profile, entity):
    entity = CoveredEntity.objects.get(ein=entity)
    associates = entity.Associations.all()
    # TODO: Do something with this old_associates
    old_associates = [
          {"Entity" : {"name" : "Cooper United"}
          , "SharedInformation" : INFORMATION_SET
          , "Purpose" : "Files paperwork regarding hospital transfers."}
        , {"Entity" : {"name" : "Sand Way", "ID" : 901}
          , "SharedInformation" : INFORMATION_SET
          , "Purpose":"Billing"}
        , {"Entity" : {"name" : "Handerson"}
          , "SharedInformation" : INFORMATION_SET
          , "Purpose":"Keeps records for HIPAA audit"}]
    return ("associates.html"
        , {"entity":entity, "associates":associates})

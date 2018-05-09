'''Heavily inspired by: https://github.com/jacobh/drf-fsm-transitions

   Modified to work with DRF >= 3.8 routing semantics
'''
from django_fsm import can_proceed
from rest_framework import exceptions
from rest_framework.decorators import action
from rest_framework.response import Response


def get_transition_viewset_method(transition_name, url_name=None, **kwargs):
    '''
    Create a viewset method for the provided `transition_name`. Requires DRF >= 3.8
    '''
    @action(detail=True, methods=['post'], url_name=url_name, url_path=transition_name, **kwargs)
    def inner_func(self, request, pk=None, **kwargs):
        object = self.get_object()
        transition_method = getattr(object, transition_name)
        if can_proceed(transition_method, self.request.user):

            # Perform the requested transition
            transition_method(request=self.request, by=self.request.user)

            if self.save_after_transition:
                object.save()
        else:
            raise exceptions.PermissionDenied(
                'User {} cannot perform transition {}'.format(self.request.user, transition_name))

        serializer = self.get_serializer(object)
        return Response(serializer.data)
    inner_func.__name__ = transition_name # Needed for DRF >= 3.8, see: router.get_routes
    return inner_func


def get_viewset_transition_action_mixin(model, **kwargs):
    '''
    Find all transitions defined on `model`, then create a corresponding
    viewset action method for each and apply it to `Mixin`. Return the Mixin.
    '''
    instance = model()

    class Mixin(object):
        save_after_transition = True

    transitions = instance.get_all_state_transitions()
    transition_names = set(x.name for x in transitions)
    for transition_name in transition_names:
        url_name = model._meta.model_name + '-' + transition_name.replace('_', '-')
        setattr(
            Mixin,
            transition_name,
            get_transition_viewset_method(transition_name, url_name=url_name, **kwargs)
        )

    return Mixin

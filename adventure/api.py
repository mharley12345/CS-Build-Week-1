from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from pusher import Pusher
from django.http import JsonResponse
from decouple import config
from django.contrib.auth.models import User
from .models import *
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers,viewsets
from rest_framework.decorators import api_view
import json
from dotenv import load_dotenv
import os


# instantiate pusher
pusher = Pusher(app_id=config('PUSHER_APP_ID'), key=config('PUSHER_KEY'), secret=config('PUSHER_SECRET'), cluster=config('PUSHER_CLUSTER'))

@csrf_exempt
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def initialize(request):
    user = request.user
    player = user.player
    player_id = player.id
    uuid = player.uuid
    room = player.room()
    players = room.playerNames(player_id)
    return JsonResponse({'uuid': uuid, 'name':player.user.username, 'title':room.title, 'description':room.description, 'players':players}, safe=True)


# @csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def move(request):
    dirs={"n": "north", "s": "south", "e": "east", "w": "west"}
    reverse_dirs = {"n": "south", "s": "north", "e": "west", "w": "east"}
    player = request.user.player
    player_id = player.id
    player_uuid = player.uuid
    data = json.loads(request.body)
    direction = data['direction']
    room = player.room()
    nextRoomID = None
    if direction == "n":
        nextRoomID = room.n_to
    elif direction == "s":
        nextRoomID = room.s_to
    elif direction == "e":
        nextRoomID = room.e_to
    elif direction == "w":
        nextRoomID = room.w_to
    if nextRoomID is not None and nextRoomID > 0:
        nextRoom = Room.objects.get(id=nextRoomID)
        player.currentRoom=nextRoomID
        player.save()
        players = nextRoom.playerNames(player_id)
        currentPlayerUUIDs = room.playerUUIDs(player_id)
        nextPlayerUUIDs = nextRoom.playerUUIDs(player_id)
        for p_uuid in currentPlayerUUIDs:
            pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{player.user.username} has walked {dirs[direction]}.'})
        for p_uuid in nextPlayerUUIDs:
            pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{player.user.username} has entered from the {reverse_dirs[direction]}.'})
        return JsonResponse({'name':player.user.username, 'title':nextRoom.title, 'description':nextRoom.description, 'players':players, 'error_msg':""}, safe=True)
    else:
        players = room.playerNames(player_id)
        return JsonResponse({'name':player.user.username, 'title':room.title, 'description':room.description, 'players':players, 'error_msg':"You cannot move that way."}, safe=True)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def say(request):
  #Implement
    player = request.user.player
    player_id = player.id
    room = player.room()
    data = json.loads(request.body)
    message = data['message']
    currUsers = room.playerNames(player_id)
    currPlayerIDs = room.playerUUIDs(player_id)
    for p_id in currPlayerIDs:
        pusher.trigger(f'p-channel-{p_id}', u'broadcast', {'message': f'{player.user.username} says to you {message}'})
    return JsonResponse({'name':player.user.username, 'title':room.title, 'description':room.description, 'players':currUsers}, safe=True)

  
class RoomSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Room
        fields = ('title','description')
    def create(self,validate_data):
        user = self.context['request'].user
        rooms = Room.objects.create(**validate_data)
        return rooms


class RoomViewSet(viewsets.ModelViewSet):

    serializer_class = RoomSerializer
    queryset= Room.objects.none()

    def get_queryset(self):
        logged_in_user = self.request.user

        if logged_in_user.is_anonymous:
            return Room.objects.none()
        else:
            return Room.objects.all()
        return get_queryset()
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def shout(request):
    """
    This function view will return the message that user say when there is a POST request to api/adv/shout
    """
    data = json.loads(request.body)
    msg = data['message']
    player = request.user.player
    player_id = player.id
    players = Player.objects.all()
    currentPlayerUUIDs =  [p.uuid for p in players if p.id != player_id]
    for p_uuid in currentPlayerUUIDs:
        pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{player.user.username} shouts: {msg}.'})
    return JsonResponse({'username': player.user.username, 'message': f'You shout: {msg}'}, safe=True)

# @csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pm(request):
    """
    This function view will return the message that user say when there is a POST request to api/adv/pm
    """
    data = json.loads(request.body)
    msg = data['message']
    player = request.user.player
    player_id = player.id
    target_username = data['username']
    try:
        target_player = User.objects.get(username = target_username)
        target_uuid = target_player.player.uuid
        pusher.trigger(f'p-channel-{target_uuid}', u'broadcast', {'message':f'{player.user.username} whispers: {msg}.'})
        return JsonResponse({'target_username': target_username, 'message': f'You whisper {target_username}: {msg}'}, safe=True)
    except User.DoesNotExist:
        return JsonResponse({'error_msg': 'This user does not exist'}, safe=True)

# @csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def whois(request):
    """
    This function view will return the message that user say when there is a POST request to api/adv/whois
    """
    data = json.loads(request.body)
    username = data['username']
    try:
        user = User.objects.get(username = username)
        player = user.player
        message = f'{username} is currently in {player.room().title}'
        return JsonResponse({'message': message}, safe=True)
    except User.DoesNotExist:
        return JsonResponse({'error_msg': 'This user does not exist'}, safe=True)
    
# @csrf_exempt
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def who(request):
    """
    This function view will return the message that user say when there is a GET request to api/adv/who
    """
    usernames = [user.username for user in User.objects.all()]
    message = ', '.join(usernames)
    return JsonResponse({'message': 'Players current online: ' + message}, safe=True)


@csrf_exempt
@api_view(["POST"])
def look(request):
    user = request.user
    player = user.player
    room = player.room()
    return JsonResponse({'items':f'{room.items}'})

@csrf_exempt
@api_view(["POST"])
def pickup(request):
    data = json.loads(request.body)
    rsp = data['message']
    user = request.user
    player = user.player
    room = player.room()
    room_items = room.items.split(' ')
    player_items = player.items.split(' ')
    rsp = rsp.split()

    if rsp[1] in room_items:
        player_items.append(rsp[1])
        updated_items = ' '.join(player_items)
        player.items = updated_items
        room_items.remove(rsp[1])
        if len(room_items) == 0:
            room.items = ''
        else:
            updated_items = ' '.join(room_items)
            room.items = updated_items
        player.save()
        room.save()
        return JsonResponse({'items':f'you picked up {rsp[1]}'})

    return JsonResponse({'items':f'no item by that name nearby'})

@csrf_exempt
@api_view(["POST"])
def drop(request):
    data = json.loads(request.body)
    rsp = data['message']
    user = request.user
    player = user.player
    room = player.room()
    room_items = room.items.split(' ')
    player_items = player.items.split(' ')
    rsp = rsp.split()

    if rsp[1] in player_items:
        room_items.append(rsp[1])
        player_items.remove(rsp[1])
        updated_items_r = ' '.join(room_items)
        room.items = updated_items_r
        room_items
        if len(player_items) == 0:
            player.items = ''
        else:
            updated_items_p = ' '.join(player_items)
            player.items = updated_items_p
        player.save()
        room.save()
        return JsonResponse({'items':f'you dropped {rsp[1]}'})
    return JsonResponse({'items':f"you don't have that item to drop"})

@csrf_exempt
@api_view(["POST"])
def inv(request):
    data = json.loads(request.body)
    user = request.user
    player = user.player
    items = player.items
    if player.items == '':
        items = 'inventory is empty'
    return JsonResponse({'items':f'{items}'})
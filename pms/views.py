from django.db.models import F, Q, Count, Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from .form_dates import Ymd
from .forms import *
from .models import Room
from .reservation_code import generate

def check_room_availability(room, checkin, checkout, exclude_booking_id=None):
    """
    Check if a room is available for the given dates
    Uses Django's date handling
    """
    # Get all confirmed bookings for this room, excluding the current booking being edited
    existing_bookings = Booking.objects.filter(
        room=room,
        state="NEW"  # Only confirmed bookings
    )
    
    if exclude_booking_id:
        existing_bookings = existing_bookings.exclude(id=exclude_booking_id)
    
    # Check for date conflicts
    for existing_booking in existing_bookings:
        # Check if dates overlap
        # Overlap occurs if:
        # - New checkin is before existing checkout AND
        # - New checkout is after existing checkin
        if (checkin < existing_booking.checkout and 
            checkout > existing_booking.checkin):
            return False
    
    return True


def calculate_booking_total(booking, checkin, checkout):
    """
    Calculate the total cost for the booking based on new dates
    Handles cases where room_type might be None
    """
    # Calculate number of nights using Django's date handling
    nights = (checkout - checkin).days
    
    try:
        # Try to get price from room_type if it exists
        if (hasattr(booking.room, 'room_type') and 
            booking.room.room_type is not None and 
            hasattr(booking.room.room_type, 'price')):
            total = nights * booking.room.room_type.price
        else:
            # Fallback: use a default price
            total = nights * 100.00  # Default price per night
    except (AttributeError, TypeError):
        # Fallback for any attribute or type errors
        total = nights * 100.00
    
    return total

class BookingSearchView(View):
    # renders search results for bookingings
    def get(self, request):
        query = request.GET.dict()
        if (not "filter" in query):
            return redirect("/")
        bookings = (Booking.objects
                    .filter(Q(code__icontains=query['filter']) | Q(customer__name__icontains=query['filter']))
                    .order_by("-created"))
        room_search_form = RoomSearchForm()
        context = {
            'bookings': bookings,
            'form': room_search_form,
            'filter': True
        }
        return render(request, "home.html", context)


class RoomSearchView(View):
    # renders the search form
    def get(self, request):
        room_search_form = RoomSearchForm()
        context = {
            'form': room_search_form
        }

        return render(request, "booking_search_form.html", context)

    # renders the search results of available rooms by date and guests
    def post(self, request):
        query = request.POST.dict()
        # calculate number of days in the hotel
        checkin = Ymd.Ymd(query['checkin'])
        checkout = Ymd.Ymd(query['checkout'])
        total_days = checkout - checkin
        # get available rooms and total according to dates and guests
        filters = {
            'room_type__max_guests__gte': query['guests']
        }
        exclude = {
            'booking__checkin__lte': query['checkout'],
            'booking__checkout__gte': query['checkin'],
            'booking__state__exact': "NEW"
        }
        rooms = (Room.objects
                 .filter(**filters)
                 .exclude(**exclude)
                 .annotate(total=total_days * F('room_type__price'))
                 .order_by("room_type__max_guests", "name")
                 )
        total_rooms = (Room.objects
                       .filter(**filters)
                       .values("room_type__name", "room_type")
                       .exclude(**exclude)
                       .annotate(total=Count('room_type'))
                       .order_by("room_type__max_guests"))
        # prepare context data for template
        data = {
            'total_days': total_days
        }
        # pass the actual url query to the template
        url_query = request.POST.urlencode()
        context = {
            "rooms": rooms,
            "total_rooms": total_rooms,
            "query": query,
            "url_query": url_query,
            "data": data
        }
        return render(request, "search.html", context)


class HomeView(View):
    # renders home page with all the bookingings order by date of creation
    def get(self, request):
        bookings = Booking.objects.all().order_by("-created")
        context = {
            'bookings': bookings
        }
        return render(request, "home.html", context)


class BookingView(View):
    @method_decorator(ensure_csrf_cookie)
    def post(self, request, pk):
        # check if customer form is ok
        customer_form = CustomerForm(request.POST, prefix="customer")
        if customer_form.is_valid():
            # save customer data
            customer = customer_form.save()
            # add the customer id to the booking form
            temp_POST = request.POST.copy()
            temp_POST.update({
                'booking-customer': customer.id,
                'booking-room': pk,
                'booking-code': generate.get()})
            # if ok, save booking data
            booking_form = BookingForm(temp_POST, prefix="booking")
            if booking_form.is_valid():
                booking_form.save()
        return redirect('/')

    def get(self, request, pk):
        # renders the form for booking confirmation.
        # It returns 2 forms, the one with the booking info is hidden
        # The second form is for the customer information

        query = request.GET.dict()
        room = Room.objects.get(id=pk)
        checkin = Ymd.Ymd(query['checkin'])
        checkout = Ymd.Ymd(query['checkout'])
        total_days = checkout - checkin
        total = total_days * room.room_type.price  # total amount to be paid
        query['total'] = total
        url_query = request.GET.urlencode()
        booking_form = BookingFormExcluded(prefix="booking", initial=query)
        customer_form = CustomerForm(prefix="customer")
        context = {
            "url_query": url_query,
            "room": room,
            "booking_form": booking_form,
            "customer_form": customer_form
        }
        return render(request, "booking.html", context)


class DeleteBookingView(View):
    # renders the booking deletion form
    def get(self, request, pk):
        booking = Booking.objects.get(id=pk)
        context = {
            'booking': booking
        }
        return render(request, "delete_booking.html", context)

    # deletes the booking
    def post(self, request, pk):
        Booking.objects.filter(id=pk).update(state="DEL")
        return redirect("/")


class EditBookingDatesView(View):
    # renders the booking edit form
    def get(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.state == "DEL":
            messages.error(request, "No se puede editar una reserva cancelada.")
            return redirect('home')
        
        error_message = None
        form = EditBookingDatesForm(instance=booking)
        context = {
            'booking': booking,
            'form': form,
            'error_message': error_message
        }

        return render(request, 'edit_booking_dates.html', context)

    # edit the booking
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        form = EditBookingDatesForm(request.POST, instance=booking)
        
        if form.is_valid():
            new_checkin = form.cleaned_data['checkin']
            new_checkout = form.cleaned_data['checkout']
            
            # Check availability for the new dates
            if check_room_availability(booking.room, new_checkin, new_checkout, exclude_booking_id=booking.id):
                # Save the form (this will update the booking)
                updated_booking = form.save(commit=False)
                
                # Recalculate total if needed
                updated_booking.total = calculate_booking_total(booking, new_checkin, new_checkout)
                updated_booking.save()
                
                messages.success(request, f"Las fechas de la reserva {booking.code} han sido actualizadas correctamente.")
                return redirect('home')
            else:
                error_message = "No hay disponibilidad para las fechas seleccionadas"
            
        context = {
            'booking': booking,
            'form': form,
            'error_message': error_message
        }
        return render(request, 'edit_booking_dates.html', context)


class EditBookingView(View):
    # renders the booking edition form
    def get(self, request, pk):
        booking = Booking.objects.get(id=pk)
        booking_form = BookingForm(prefix="booking", instance=booking)
        customer_form = CustomerForm(prefix="customer", instance=booking.customer)
        context = {
            'booking_form': booking_form,
            'customer_form': customer_form

        }
        return render(request, "edit_booking.html", context)

    # updates the customer form
    @method_decorator(ensure_csrf_cookie)
    def post(self, request, pk):
        booking = Booking.objects.get(id=pk)
        customer_form = CustomerForm(request.POST, prefix="customer", instance=booking.customer)
        if customer_form.is_valid():
            customer_form.save()
            return redirect("/")


class DashboardView(View):
    def get(self, request):
        from datetime import date, time, datetime
        today = date.today()

        # get bookings created today
        today_min = datetime.combine(today, time.min)
        today_max = datetime.combine(today, time.max)
        today_range = (today_min, today_max)
        new_bookings = (Booking.objects
                        .filter(created__range=today_range)
                        .values("id")
                        ).count()

        # get incoming guests
        incoming = (Booking.objects
                    .filter(checkin=today)
                    .exclude(state="DEL")
                    .values("id")
                    ).count()

        # get outcoming guests
        outcoming = (Booking.objects
                     .filter(checkout=today)
                     .exclude(state="DEL")
                     .values("id")
                     ).count()

        # get outcoming guests
        invoiced = (Booking.objects
                    .filter(created__range=today_range)
                    .exclude(state="DEL")
                    .aggregate(Sum('total'))
                    )

        # preparing context data
        dashboard = {
            'new_bookings': new_bookings,
            'incoming_guests': incoming,
            'outcoming_guests': outcoming,
            'invoiced': invoiced

        }

        context = {
            'dashboard': dashboard
        }
        return render(request, "dashboard.html", context)


class RoomDetailsView(View):
    def get(self, request, pk):
        # renders room details
        room = Room.objects.get(id=pk)
        bookings = room.booking_set.all()
        context = {
            'room': room,
            'bookings': bookings}
        print(context)
        return render(request, "room_detail.html", context)


class RoomsView(View):
    def get(self, request):
        # renders a list of rooms
        rooms = Room.objects.all().values("name", "room_type__name", "id")
        context = {
            'rooms': rooms
        }
        return render(request, "rooms.html", context)

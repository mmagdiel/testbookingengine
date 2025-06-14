from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.http import HttpRequest, QueryDict, JsonResponse

from pms.views import (
    BookingSearchView, RoomSearchView, HomeView, BookingView,
    DeleteBookingView, EditBookingView, DashboardView,
    RoomDetailsView, RoomsView, RoomsSearch
)


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
    STATIC_URL='/static/',
    USE_STATIC_IN_TESTS=False
)
class BaseViewTest(TestCase):
    """Base test class with common setup for all view tests"""
    
    def setUp(self):
        self.mock_render_patcher = patch('pms.views.render')
        self.mock_render = self.mock_render_patcher.start()
        
        from django.http import HttpResponse
        self.mock_render.return_value = HttpResponse('Mocked response')
        
    def tearDown(self):
        self.mock_render_patcher.stop()


class BookingSearchViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = BookingSearchView()
        
    def test_get_without_filter_redirects_home(self):
        """Test that GET request without filter parameter redirects to home"""
        self.mock_render_patcher.stop()
        
        request = HttpRequest()
        request.method = 'GET'
        request.GET = QueryDict('')
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        
        # Restart the patcher for other tests
        self.mock_render_patcher.start()
    
    @patch('pms.models.Booking.objects')
    def test_get_with_filter_returns_results(self, mock_booking_objects):
        """Test that GET request with filter returns booking results"""
        mock_bookings = MagicMock()
        mock_booking_objects.filter.return_value.order_by.return_value = mock_bookings
        
        request = HttpRequest()
        request.method = 'GET'
        request.GET = QueryDict('filter=test123')
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        mock_booking_objects.filter.assert_called_once()

        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[1], "home.html") 
        self.assertIn('bookings', args[2]) 


class RoomSearchViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = RoomSearchView()
        
    def test_get_renders_search_form(self):
        """Test that GET request renders the search form"""
        request = HttpRequest()
        request.method = 'GET'
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[1], "booking_search_form.html")
        
    @patch('pms.models.Room.objects')
    @patch('pms.views.Ymd.Ymd')
    def test_post_with_valid_data(self, mock_ymd, mock_room_objects):
        """Test POST request with valid search data"""

        mock_ymd.return_value = 4 
        

        mock_rooms = MagicMock()
        mock_room_objects.filter.return_value.exclude.return_value.annotate.return_value.order_by.return_value = mock_rooms
        mock_room_objects.filter.return_value.values.return_value.exclude.return_value.annotate.return_value.order_by.return_value = mock_rooms
        
        request = HttpRequest()
        request.method = 'POST'
        request.POST = QueryDict('checkin=2024-12-01&checkout=2024-12-05&guests=2')
        
        response = self.view.post(request)
        
        self.assertEqual(response.status_code, 200)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[1], "search.html")


class HomeViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = HomeView()
        
    @patch('pms.models.Booking.objects')
    def test_get_renders_bookings(self, mock_booking_objects):
        """Test that GET request renders all bookings"""
        mock_bookings = MagicMock()
        mock_booking_objects.all.return_value.order_by.return_value = mock_bookings
        
        request = HttpRequest()
        request.method = 'GET'
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        mock_booking_objects.all.assert_called_once()
        self.mock_render.assert_called_once()


class BookingViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = BookingView()
        
    @patch('pms.models.Room.objects')
    @patch('pms.views.Ymd.Ymd')
    def test_get_booking_form(self, mock_ymd, mock_room_objects):
        """Test GET request for booking form"""
        mock_ymd.return_value = 4 
        
        mock_room = MagicMock()
        mock_room.room_type.price = Decimal('100.00')
        mock_room_objects.get.return_value = mock_room
        
        request = HttpRequest()
        request.method = 'GET'
        request.GET = QueryDict('checkin=2024-12-01&checkout=2024-12-05&guests=2')
        
        response = self.view.get(request, pk=1)
        
        self.assertEqual(response.status_code, 200)
        self.mock_render.assert_called_once()
        
    @patch('pms.views.CustomerForm')
    @patch('pms.views.BookingForm')
    @patch('pms.views.generate.get')
    def test_post_valid_booking(self, mock_generate, mock_booking_form, mock_customer_form):
        """Test POST request with valid booking data"""
        self.mock_render_patcher.stop()
        
        mock_customer = MagicMock()
        mock_customer.id = 1
        mock_customer_form.return_value.is_valid.return_value = True
        mock_customer_form.return_value.save.return_value = mock_customer
        
        mock_booking_form.return_value.is_valid.return_value = True
        mock_generate.return_value = 'BOOK123'
        
        request = HttpRequest()
        request.method = 'POST'
        request.POST = QueryDict('customer-name=John&customer-email=john@test.com')
        
        response = self.view.post(request, pk=1)
        
        self.assertEqual(response.status_code, 302) 
        self.assertEqual(response.url, '/')
        
        self.mock_render_patcher.start()


class DeleteBookingViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = DeleteBookingView()
        
    @patch('pms.models.Booking.objects')
    def test_get_delete_form(self, mock_booking_objects):
        """Test GET request for delete confirmation form"""
        mock_booking = MagicMock()
        mock_booking_objects.get.return_value = mock_booking
        
        request = HttpRequest()
        request.method = 'GET'
        
        response = self.view.get(request, pk=1)
        
        self.assertEqual(response.status_code, 200)
        self.mock_render.assert_called_once()
        
    @patch('pms.models.Booking.objects')
    def test_post_delete_booking(self, mock_booking_objects):
        """Test POST request to delete booking"""
        self.mock_render_patcher.stop()
        
        request = HttpRequest()
        request.method = 'POST'
        
        response = self.view.post(request, pk=1)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        mock_booking_objects.filter.assert_called_once_with(id=1)
        mock_booking_objects.filter.return_value.update.assert_called_once_with(state="DEL")
        
        self.mock_render_patcher.start()


class EditBookingViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = EditBookingView()
        
    @patch('pms.models.Booking.objects')
    def test_get_edit_form(self, mock_booking_objects):
        """Test GET request for edit booking form"""
        mock_booking = MagicMock()
        mock_booking.customer = MagicMock()
        mock_booking_objects.get.return_value = mock_booking
        
        request = HttpRequest()
        request.method = 'GET'
        
        response = self.view.get(request, pk=1)
        
        self.assertEqual(response.status_code, 200)
        self.mock_render.assert_called_once()
        
    @patch('pms.models.Booking.objects')
    @patch('pms.views.CustomerForm')
    def test_post_edit_booking_valid(self, mock_customer_form, mock_booking_objects):
        """Test POST request with valid edit data"""
        self.mock_render_patcher.stop()
        
        mock_booking = MagicMock()
        mock_booking.customer = MagicMock()
        mock_booking_objects.get.return_value = mock_booking
        
        mock_customer_form.return_value.is_valid.return_value = True
        
        request = HttpRequest()
        request.method = 'POST'
        request.POST = QueryDict('customer-name=Jane&customer-email=jane@test.com')
        
        response = self.view.post(request, pk=1)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        mock_customer_form.return_value.save.assert_called_once()
        
        self.mock_render_patcher.start()


class DashboardViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = DashboardView()
        
    @patch('pms.models.Booking.objects')
    def test_get_dashboard_data(self, mock_booking_objects):
        """Test GET request returns dashboard statistics"""
        mock_booking_objects.filter.return_value.values.return_value.count.return_value = 5
        mock_booking_objects.filter.return_value.exclude.return_value.values.return_value.count.return_value = 3
        mock_booking_objects.filter.return_value.exclude.return_value.aggregate.return_value = {'total__sum': Decimal('1500.00')}
        
        request = HttpRequest()
        request.method = 'GET'
        
        import datetime as dt_module
        with patch.object(dt_module, 'date') as mock_date, \
             patch.object(dt_module, 'time') as mock_time, \
             patch.object(dt_module, 'datetime') as mock_datetime:
            
            mock_date.today.return_value = date(2024, 12, 1)
            mock_time.min = time.min
            mock_time.max = time.max  
            mock_datetime.combine.return_value = datetime(2024, 12, 1, 12, 0, 0)
            
            response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.mock_render.assert_called_once()


class RoomDetailsViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = RoomDetailsView()
        
    @patch('pms.models.Room.objects')
    def test_get_room_details(self, mock_room_objects):
        """Test GET request for room details"""
        mock_room = MagicMock()
        mock_room.booking_set.all.return_value = []
        mock_room_objects.get.return_value = mock_room
        
        request = HttpRequest()
        request.method = 'GET'
        
        response = self.view.get(request, pk=1)
        
        self.assertEqual(response.status_code, 200)
        self.mock_render.assert_called_once()


class RoomsViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = RoomsView()
        
    @patch('pms.models.Room.objects')
    def test_get_rooms_list(self, mock_room_objects):
        """Test GET request returns list of rooms"""
        mock_rooms = [
            {'name': 'Room 101', 'room_type__name': 'Standard', 'id': 1},
            {'name': 'Room 102', 'room_type__name': 'Deluxe', 'id': 2}
        ]
        mock_room_objects.all.return_value.values.return_value = mock_rooms
        
        request = HttpRequest()
        request.method = 'GET'
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.mock_render.assert_called_once()


class RoomsSearchTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.view = RoomsSearch()
        
    @patch('pms.models.Room.objects')
    def test_search_rooms_by_name(self, mock_room_objects):
        """Test searching rooms by name"""
        mock_rooms = [
            {'name': 'Room 101', 'room_type__name': 'Standard', 'id': 1}
        ]
        mock_room_objects.filter.return_value.values.return_value = mock_rooms
        
        request = HttpRequest()
        request.method = 'GET'
        request.GET = QueryDict('by=  room 101  ')
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.mock_render.assert_called_once()
        
        mock_room_objects.filter.assert_called_once_with(name__contains='Room 101')
        


class ViewLogicTest(TestCase):
    """Test view logic without template rendering"""
    
    def test_views_can_be_imported(self):
        """Test that all views can be imported successfully"""
        self.assertTrue(BookingSearchView)
        self.assertTrue(RoomSearchView)
        self.assertTrue(HomeView)
        self.assertTrue(BookingView)
        self.assertTrue(DeleteBookingView)
        self.assertTrue(EditBookingView)
        self.assertTrue(DashboardView)
        self.assertTrue(RoomDetailsView)
        self.assertTrue(RoomsView)
        self.assertTrue(RoomsSearch)
    
    def test_booking_search_redirect_logic(self):
        """Test the redirect logic in BookingSearchView"""
        view = BookingSearchView()
        request = HttpRequest()
        request.method = 'GET'
        request.GET = QueryDict('')
        
        response = view.get(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
    
    @patch('pms.models.Room.objects')
    def test_rooms_search_parameter_processing(self, mock_room_objects):
        """Test that RoomsSearch properly processes the 'by' parameter"""
        mock_room_objects.filter.return_value.values.return_value = []
        
        view = RoomsSearch()
        request = HttpRequest()
        request.method = 'GET'
        request.GET = QueryDict('by=  test room  ')
        
        with patch('pms.views.render') as mock_render:
            mock_render.return_value = MagicMock()
            view.get(request)

        mock_room_objects.filter.assert_called_once_with(name__contains='Test room')


# Integration tests that test multiple components together
class ViewIntegrationTest(TestCase):
    """Integration tests for view workflows"""
    
    @patch('pms.views.render')
    @patch('pms.models.Room.objects')
    @patch('pms.models.Booking.objects')
    def test_booking_workflow_data_flow(self, mock_booking_objects, mock_room_objects, mock_render):
        """Test data flow in booking workflow"""
        from django.http import HttpResponse
        mock_render.return_value = HttpResponse('Mock')
        
        # Mock room search
        mock_room = MagicMock()
        mock_room.id = 1
        mock_room.room_type.price = Decimal('100.00')
        mock_room_objects.filter.return_value.exclude.return_value.annotate.return_value.order_by.return_value = [mock_room]
        mock_room_objects.get.return_value = mock_room
        
        # Test room search
        search_view = RoomSearchView()
        request = HttpRequest()
        request.method = 'POST'
        request.POST = QueryDict('checkin=2024-12-01&checkout=2024-12-05&guests=2')
        
        with patch('pms.views.Ymd.Ymd', return_value=4):
            response = search_view.post(request)
            
        self.assertEqual(response.status_code, 200)
        
        booking_view = BookingView()
        request.method = 'GET'
        request.GET = QueryDict('checkin=2024-12-01&checkout=2024-12-05&guests=2')
        
        with patch('pms.views.Ymd.Ymd', return_value=4):
            response = booking_view.get(request, pk=1)
            
        self.assertEqual(response.status_code, 200)
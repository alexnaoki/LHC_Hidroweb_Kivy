from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.network.urlrequest import UrlRequest
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, StringProperty
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.button import Button
from kivy.base import ExceptionHandler, ExceptionManager

from mapview import MapMarker, MapView
from mapview.clustered_marker_layer import ClusteredMarkerLayer
from mapview.geojson import GeoJsonMapLayer

import pandas as pd
from shapely.geometry import shape,mapping, Point, Polygon, MultiPolygon
import shapefile
from json import dumps
from requests.models import PreparedRequest
import xml.etree.ElementTree as ET
import datetime
import calendar
import threading
import csv
import time

class MainScreen(Screen):
    layer = ClusteredMarkerLayer(cluster_node_size=4,cluster_radius=200)
    popup = ObjectProperty()

    def open_popup(self):
        self.popup = CustomPopup()
        self.popup.open()

    def show_inventario_cluster(self):
        print(self.popup.inventario_path)
        # self.df_inventario = pd.read_csv(self.popup.inventario_path)
        # for i, row in self.df_inventario.iterrows():
        self.ids['progressbar'].value = 25

        with open(self.popup.inventario_path, encoding='utf8') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                self.layer.add_marker(lat=float(row['Latitude']), lon=float(row['Longitude']))
        print('Added to layer')
        self.ids['map'].add_widget(self.layer)
        self.layer.reposition()

        print('Added Layer')
        self.ids['progressbar'].value = 50

    def open_popup_shp(self):
        self.popup_shp = ShapefilePopup()
        self.popup_shp.open()

    def check_within_shp(self):
        shp_path = self.popup_shp.shapefile_path
        shp = shapefile.Reader(shp_path)
        print(shp)
        self.codes = []
        all_shapes = shp.shapes()
        all_records = shp.records()
        print(all_shapes)
        print(all_records)

        for i in range(len(all_shapes)):
            boundary = all_shapes[i]
            boundary = shape(boundary)
            print(boundary)
            with open(self.popup.inventario_path, encoding='utf8') as csvfile:
                data = csv.DictReader(csvfile)
                for row in data:
                    if Point((float(row['Longitude']), float(row['Latitude']))).within(boundary):
                        print('Dentro')
                        print(float(row['Latitude']), float(row['Longitude']), int(row['Codigo']))
                        mark = MapMarker(lat=float(row['Latitude']), lon=float(row['Longitude']))
                        self.ids['map'].add_marker(mark)
                        self.codes.append(int(row['Codigo']))
                    else:
                        pass
        print(self.codes)

    def download_ANA_station(self):
        typeData=2
        list_codes = self.codes
        for station in list_codes:
            api = 'http://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroSerieHistorica'
            self.params = {'codEstacao': station, 'dataInicio': '', 'dataFim': '', 'tipoDados': '{}'.format(typeData), 'nivelConsistencia': ''}
            url_req = PreparedRequest()
            url_req.prepare_url(api, self.params)
            self.req = UrlRequest(
                            url_req.url,
                            on_success=self._download_sucess,
                            # on_success=self._donwload_teste,
                            on_error=self._download_error,
                            on_failure=self._download_error
                             )
            # print(self.req)
            # self.req.wait()
            print(station)
    def _donwload_teste(self, req, result):
        print('sucesso')
        print(result)

    def _download_sucess(self, req, result):
        try:
            # print(self.req.result)
            tree = ET.ElementTree(ET.fromstring(result))
            # print(tree)
            root = tree.getroot()

            list_data = []
            list_consistenciaF = []
            list_month_dates = []
            for i in root.iter('SerieHistorica'):
                codigo = i.find("EstacaoCodigo").text
                consistencia = i.find("NivelConsistencia").text
                date = i.find("DataHora").text
                date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                last_day = calendar.monthrange(date.year, date.month)[1]
                month_dates = [date + datetime.timedelta(days=i) for i in range(last_day)]
                data = []
                list_consistencia = []
                for day in range(last_day):
                    # if params['tipoDados'] == '3':
                    #     value = 'Vazao{:02}'.format(day+1)
                    #     try:
                    #         data.append(float(i.find(value).text))
                    #         list_consistencia.append(int(consistencia))
                    #     except TypeError:
                    #         data.append(i.find(value).text)
                    #         list_consistencia.append(int(consistencia))
                    #     except AttributeError:
                    #         data.append(None)
                    #         list_consistencia.append(int(consistencia))
                    if self.params['tipoDados'] == '2':
                        value = 'Chuva{:02}'.format(day+1)
                        try:
                            data.append(float(i.find(value).text))
                            list_consistencia.append(consistencia)
                        except TypeError:
                            data.append(i.find(value).text)
                            list_consistencia.append(consistencia)
                        except AttributeError:
                            data.append(None)
                            list_consistencia.append(consistencia)
                list_data = list_data + data
                list_consistenciaF = list_consistenciaF + list_consistencia
                list_month_dates = list_month_dates + month_dates
            typeData = 2
            print(list_data)
            print(list_month_dates)
            print(list_consistenciaF)
            if len(list_data) > 0:
                df = pd.DataFrame({'Date': list_month_dates, 'Consistence_{}_{}'.format(typeData,codigo): list_consistenciaF, 'Data{}_{}'.format(typeData, codigo): list_data})
                print(df.to_csv(f'{codigo}_teste.csv'))
        except:
            print('ERRO')

    def _download_error(self, *args):
        print('ERRO download')



class CustomPopup(Popup):
    def select_inventario(self, selection, *args):
        try:
            self.inventario_path = selection[0]
            print(self.inventario_path)
            print('Selecionado Inventario')
        except:
            print('erro popup')

class ShapefilePopup(Popup):
    def select_shapefile(self, selection, *args):
        try:
            self.shapefile_path = selection[0]
            print(self.shapefile_path)
            print('Selecionado Shapefile')
        except:
            print('erro popup shapefile')

class WindowManager(ScreenManager):
    pass

class RootApp(App):
    def build(self):
        return Builder.load_file('main.kv')


# class E(ExceptionHandler):
#     def handle_exception(self, inst):
#         app = App.get_running_app()
#         if app.scheduled_switch is not None:
#             app.scheduled_switch.cancel()  # cancel the scheduled switch
#             app.scheduled_switch = None
#         if app.Exception_counter == 0:
#             popup = MsgPopup(inst)
#             popup.open()
#         app.Exception_counter += 1
#         return ExceptionManager.PASS
#
# ExceptionManager.add_handler(E())
RootApp().run()

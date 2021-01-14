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
from kivy.clock import mainthread

from mapview import MapMarker, MapView
from mapview.clustered_marker_layer import ClusteredMarkerLayer
from mapview.geojson import GeoJsonMapLayer

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
import os

class MainScreen(Screen):
    layer = ClusteredMarkerLayer(cluster_node_size=4,cluster_radius=200)
    popup = ObjectProperty()
    mapa = ObjectProperty()

    def change_toInventario(self):
        self.manager.current = 'inventario'

    def change_toShape(self):
        self.manager.current = 'shapefilescreen'

    def change_toDownload_shp(self):
        self.manager.current = 'downloadscreen_shp'

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
                # df = pd.DataFrame({'Date': list_month_dates, 'Consistence_{}_{}'.format(typeData,codigo): list_consistenciaF, 'Data{}_{}'.format(typeData, codigo): list_data})
                # print(df.to_csv(f'{codigo}_teste.csv'))
                rows = zip(list_month_dates, list_consistenciaF, list_data)
                with open(f'{codigo}_teste_sempandas.csv', 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(('Date', f'Consistence_{typeData}_{codigo}', f'Data_{codigo}'))
                    for row in rows:
                        writer.writerow(row)
        except:
            print('ERRO')

    def _download_error(self, *args):
        print('ERRO download')

    @mainthread
    def set_screen(self):
        self.manager.current = 'main'

    def show_codes(self):
        print(self.manager.get_screen('shapefilescreen').codes)


class WindowManager(ScreenManager):
    pass

class LoadingScreen(Screen):
    pass

class InventarioScreen(Screen):
    layer = ClusteredMarkerLayer(cluster_node_size=4,cluster_radius=200)
    inventario_path = StringProperty('')

    def teste(self):
        mark = MapMarker(lat=50, lon=10)
        self.manager.get_screen('main').ids['map'].add_marker(mark)

    def show_inventarioCluster(self, selection, *args):
        # print(selection)
        # self.manager.current = 'loading'
        # print(self.popup.inventario_path)
        # print(filechooserscreen.selection[0])

        # self.ids['progressbar'].value = 25
        self.inventario_path = selection[0]
        with open(self.inventario_path, encoding='utf8') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                self.layer.add_marker(lat=float(row['Latitude']), lon=float(row['Longitude']))
        print('Added to layer')
        # self.ids['map'].add_widget(self.layer)
        self.manager.get_screen('main').ids['map'].add_widget(self.layer)
        self.layer.reposition()
        print('Added Layer')
        self.manager.current = 'main'
        self.manager.transition.direction = "left"
        # self.ids['progressbar'].value = 50

class ShapefileScreen(Screen):
    codes = []
    def get_codes(self, selection, *args):
        print(selection[0])
        shp_path = selection[0]
        shp = shapefile.Reader(shp_path)
        print(shp)

        all_shapes = shp.shapes()
        all_records = shp.records()
        print(all_shapes)
        print(all_records)
        print(self.manager.get_screen('inventario').ids.filechooserscreen.selection[0])
        for i in range(len(all_shapes)):
            boundary = all_shapes[i]
            boundary = shape(boundary)
            print(boundary)
            with open(self.manager.get_screen('inventario').ids.filechooserscreen.selection[0], encoding='utf8') as csvfile:
                data = csv.DictReader(csvfile)
                for row in data:
                    if Point((float(row['Longitude']), float(row['Latitude']))).within(boundary):
                        print('Dentro')
                        print(float(row['Latitude']), float(row['Longitude']), int(row['Codigo']))
                        mark = MapMarker(lat=float(row['Latitude']), lon=float(row['Longitude']))
                        self.manager.get_screen('main').ids['map'].add_marker(mark)
                        self.codes.append(int(row['Codigo']))
                    else:
                        pass
        print(self.codes)
        self.manager.current = 'main'
        self.manager.transition.direction = "right"

class DownloadScreenShp(Screen):
    def selected(self, directory, filename):
        self.ids.downloadShpPath.text = os.path.dirname(filename)

    def teste(self):
        folder_name = 'dados_LHC_hidroweb'

        self.save_folder = os.path.join(self.ids.downloadShpPath.text, folder_name)
        if not os.path.exists(self.save_folder):
            print('nao existe')
            os.mkdir(self.save_folder)
        else:
            print('existe')


    def download_ANA_station(self):
        folder_name = 'dados_LHC_hidroweb'
        self.save_folder = os.path.join(self.ids.downloadShpPath.text, folder_name)
        if not os.path.exists(self.save_folder):
            print('nao existe, criando pasta')
            os.mkdir(self.save_folder)
        else:
            print('existe')

        typeData=2
        list_codes = self.manager.get_screen('shapefilescreen').codes
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
            tree = ET.ElementTree(ET.fromstring(result))
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
                # df = pd.DataFrame({'Date': list_month_dates, 'Consistence_{}_{}'.format(typeData,codigo): list_consistenciaF, 'Data{}_{}'.format(typeData, codigo): list_data})
                # print(df.to_csv(f'{codigo}_teste.csv'))
                rows = zip(list_month_dates, list_consistenciaF, list_data)
                with open(os.path.join(self.save_folder,f'{codigo}_teste_sempandas.csv'), 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(('Date', f'Consistence_{typeData}_{codigo}', f'Data_{codigo}'))
                    for row in rows:
                        writer.writerow(row)
        except:
            print('ERRO')

    def _download_error(self, *args):
        print('ERRO download')

class RootApp(App):
    def build(self):
        return Builder.load_file('main.kv')

RootApp().run()

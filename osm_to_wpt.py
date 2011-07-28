# http://gis-lab.info/qa/ogr-python.html
# -*- coding: utf-8 -*-

#from osgeo import gdal
#from osgeo import ogr
#from osgeo import osr
#from osgeo import gdal_array
#from osgeo import gdalconst

#import gdal
#import ogr
#import osr
#import gdalnumeric
#import gdalconst

# Скрипт для конвертации точек из OSM в wpt-файл.

# Массив name_types содержит соответствие name и иконки в Ozi (пока для Garmin)
# Массив ignore_types содержит name, которые не должны попадать в выходной файл.

import sys, os.path, argparse
import osgeo.ogr as ogr

type_notfound = 0
poi_passed = 0
total_pocessed = 1
poi_ignored = 0
poi_skipped = 0
not_found_list = []
poi_converted = 0

head = 'OziExplorer Waypoint File Version 1.1\nWGS 84\nReserved 2\ngarmin\n'

# имя типа, id иконки в ozi
# ford = брод - зеленый круг
# speed_camera = замер скорости - красный круг
# traffic_signals = светофор на перекрестке, ЖД переезде - красный куб
# waste_basket, waste_disposal = сбор мусора - зеленый куб
# ferry_terminal = паромная переправа - синий круг

name_types = [['fuel', 25], ['traffic_signals', 146], ['post_office', 44], ['bank', 2], ['telephone', 63],  ['emergency_phone', 63], ['cafe', 3],
              ['pharmacy', 106], ['place_of_worship', 12], ['restaurant', 47], ['police', 151], ['parking', 42], ['bar', 3], ['pub', 3],
              ['speed_camera', 165], ['crossing', 18], ['car_wash', 0], ['drinking_water', 21], ['fast_food', 22],
			  ['marketplace', 55], ['shop', 55], ['toilets', 48], ['car_repair', 10], ['hospital', 36],['clinic', 36], ['doctors', 36],
		['ford', 166], ['waste_basket', 148], ['waste_disposal', 148], ['ferry_terminal', 167]]

# имена типов, которые не попадут в выходной файл
ignore_types = ['bus_stop', 'place_of_worship', 'school', 'library', 'street_lamp', 'university', 'courthouse', 'bench', 'bus_station', 'fire_station', 'kindergarten',\
				'bicycle_parking', 'turning_circle', 'public_building', 'cinema', 'steps', 'incline', 'platform', 'embassy', 'townhall', 'post_box', 'theatre',
				'fountain', 'arts_centre', 'taxi', 'sauna', 'bank', 'lamp', 'dentist', 'college']

# хранит статистику: сколько каких типов не удалось определить,
class not_found_stat:
	def __init__(self, name):
		self.name = name
		self.count = 1
	count = 0				# Количество совпадений
	name = ''				# Имя типа

# Проверка на присутствие необходимых файлов
def check_input_files(in_path, base_filename):

	isError = False
	file_ext = ['.shp', '.shp', '.dbf']

	for file in file_ext:
		filename = os.path.join( os.path.dirname(in_path), base_filename + file );
		if not os.access(filename, os.R_OK):
			print "Not access to file: " + filename
			isError = True
	return isError

# Перекодировка из  utf-8 в win1251
def utf8_to_win(utf8):
	s_uni = utf8.decode('utf8')
	try:
		s_cp1251 = s_uni.encode('cp1251')
		return s_cp1251
	except ValueError:
		print "Oops! Error encode: [" + utf8 + "]"	# бывает и такое
		return utf8
#	return s_cp1251
#	return utf8

# Меняем текстовый тип на цифру для Garmin
def get_type(name, osmId):
	global type_notfound
	global poi_passed
	global not_found_list

	for name_type in name_types:
		if name_type[0] == name:
			poi_passed += 1
			return ('%d' % (name_type[1]))
#	print 'get_type: [' + name + '] not found'
#	print ('Type: (%d) [' % (type_notfound)) + name + '] not found'
	type_notfound += 1
	if len(not_found_list) == 0:
		new_item = not_found_stat(name)
		not_found_list.append(new_item)
#		print "type not found of OSM_ID: " + osmId + " <=> " + name
	else:
		is_new_item = False
		for not_found_item in not_found_list:
			if not_found_item.name == name:
				not_found_item.count += 1
				return '0'
		new_item = not_found_stat(name)
		print "type not found of OSM_ID: " + osmId + " <=> " + name
		not_found_list.append(new_item)
	return '0'

# Проверка на игнорироваание типа.
def is_ignore(name):
	global poi_ignored
	for item in ignore_types:
		if item == name:
			poi_ignored += 1
			return True
	return False

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='OSM to wpt data convertor.')
	parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.1a')
	parser.add_argument('infile', help='Input file')
	parser.add_argument('-o', help='Output file')
	parser.add_argument('-f', action='append', nargs = 2, help='filter tag: -f amenity fuel [-f amenity parking]')
	args = parser.parse_args()

	counter = 1												# счетчик строк wpt-файла
	out_path = ''
	in_path = args.infile									# извлекаем имя входного файла из командной строки

	if in_path.find('.') == -1:
		in_path += '.shp'									# добисываем расширение, если его нет
	
	base_filename = os.path.splitext(os.path.basename(in_path))[0]

	if args.o != None:
		out_path = args.o									# извлекаем имя выходного файла из командной строки, если оно было указано
	else:
		out_path = os.path.join( os.path.dirname(in_path), base_filename + '.wpt' )	# иначе располагаем его рядом с входными данными

	if check_input_files(in_path, base_filename):			# проверяем доступны ли все нужные файлы
		sys.exit( 1 )

	ogrData = ogr.Open( in_path, False )
	f = open( out_path, 'w' )

	if ogrData is None:										# проверяем все ли в порядке
		print "ERROR: open : [" + in_path + "] failed"
		sys.exit( 1 )

	print "Number of layers", ogrData.GetLayerCount()
	layer = ogrData.GetLayer( 0 )
	if layer is None:
		print "ERROR: can't access layer"
		sys.exit( 1 )
	
	layer.ResetReading()

	query = ''

	if args.f != None:										# извлекаем фильтры из командной строки
		for item in args.f:
			query += item[0] + '=' + item[1] + ' OR '

	query = query[:len(query)-4]
	print "Query :" + query

	if len(query) > 0:
		layer.SetAttributeFilter( query )

	# начинаем просматривать объекты в исходном слое
	inFeat = layer.GetNextFeature()
	f.write( head ) # write wpt head

	# собственно цикл в котором и перебираем объекты, удовлетворяющие
	# условию фильтра
	feat = layer.GetNextFeature()
	featDef = layer.GetLayerDefn() # схема (таблица атрибутов) слоя
	while feat is not None:
		type = ''		# тип точки fuel, telephone и т.д.
		name = ''		# osm:name
		xPos = ''		# lat
		yPos = ''		# lon
		osmId = ''		# OSM_ID - идентификатор точки
		for i in range( featDef.GetFieldCount() ): # проходим по всем полям
			fieldDef = featDef.GetFieldDefn(i) # получаем i-тое поле
			field_name = fieldDef.GetNameRef() # и выводим информацию
			field_value = feat.GetFieldAsString(i)
			if len(field_value) > 0:
				if field_name == 'OSM_ID':
					osmId = field_value			# сохраняем OSM_ID
					geom = feat.GetGeometryRef()
					if geom is None:
						print "Invalid geometry"
					if geom.GetGeometryType() == ogr.wkbPoint:
						xPos = geom.GetX()		# сохраняем широту
						yPos = geom.GetY()		# сохраняем долготу
						coords = "%.7f, %.7f" % ( geom.GetY(), geom.GetX() )
					else:
						print "Non point geometry"
				elif field_name == 'HIGHWAY' or field_name == 'AMENITY' :	# Нам нужны тольк они
					type = field_value						# сохраняем тип
	#			print 'field_name: ' + field_name
				if field_name == 'NAME':
					name = field_value						# сохраняем name
	#			print field_name + ' - ' + field_value
		if len(type) > 0 and not is_ignore(type):
			wpt_type = get_type(type, osmId)				# Преобразуем тип в ozi
			
			wpt_line = ('%d, ' % (counter))					# Добавляем номер строки
			if len(name) > 0:
				wpt_line += ('%s, ' % (utf8_to_win(name)))	# Если есть имя, то указываем его
			else:
				wpt_line += ('%s, ' % (type))				# иначе указываем тип
			wpt_line += ('%s, ' % (coords))					# добавляем координаты
			wpt_line += '40741.9547917, '					# пока без изменений
			wpt_line += ('%s, ' % (wpt_type))				# иконка

			wpt_line += '0, '								# пока без изменений
			if wpt_type == '0':								# если тип не найден
				wpt_line += '3, '							# отображать точку
			else:
				wpt_line += '4, '							# отображать иконку

			wpt_line += '0, 65535, '							# пока без изменений
			wpt_line += ('%s, ' % (utf8_to_win(name)))		# вставляем имя в комментарий. вот только зачем...
			wpt_line += '0, 0, '								# пока без изменений

			if wpt_type == '165':							# Если точка speed_camera
				wpt_line += '500, '							# отрисовываем вокруг нее
			else:
				wpt_line += '0, '							# ни чего необычного
				
			wpt_line += '-777, 6, 0,17,0,10.0,2,,,\n'		# пока без изменений
			f.write( wpt_line )								# пишем в выходной файл
			poi_converted += 1
			counter += 1
		else:
			poi_skipped += 1
	#		print "Skip: " + field_name + " : " + field_value
		feat = layer.GetNextFeature() # переходим к следующему объекту
		total_pocessed += 1
#		print ('object pocessed:  %d' % (total_pocessed))
	f.close()

	print ":::::::::::::::::::::::::"
	print "Feature count: ", layer.GetFeatureCount()
	print ('total_pocessed: %d' % (total_pocessed))
	print ('poi_converted: %d, (passed: %d, type_notfound: %d)' % (poi_converted, poi_passed, type_notfound))
	print ('poi_skipped: %d, (ignored: %d)' % (poi_skipped, poi_ignored))
	print ('not_found_list size: %d' % (len(not_found_list)))
	for item in not_found_list:
	#	print item.name + ' [' + item.count + ']'
		print ('[%3d] %s' % (item.count, item.name))

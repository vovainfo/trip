import datetime as dt
import requests
import json

BASE_URL: str = 'https://aerodatabox.p.rapidapi.com/flights/airports/icao/'


def parse_one_flight(one_flight) -> {}:
    new_item = {'time_departure': dt.datetime.strptime(one_flight['departure']['scheduledTimeLocal'], '%Y-%m-%d %H:%M%z'),
                'time_arrival': dt.datetime.strptime(one_flight['arrival']['scheduledTimeLocal'], '%Y-%m-%d %H:%M%z'),
                'flight_number': one_flight['number'],
                'airlaine_name': one_flight['airline']['name']}

    try:
        new_item['aircraft_model'] = one_flight['aircraft']['model']
    except KeyError:
        new_item['aircraft_model'] = 'Unknown'
    return new_item


def date_convert_json(o):
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()


def get_route_list(base_airport: str, minimum_departure_date: str, maximum_return_date: str, minimum_stay: str) -> str:
    min_date = dt.datetime.strptime(minimum_departure_date, '%Y-%m-%dT%H:%M')
    max_date = dt.datetime.strptime(maximum_return_date, '%Y-%m-%dT%H:%M')
    min_stay = dt.timedelta(hours=int(minimum_stay))

    cur_date = min_date  # начало периода при обращении к API
    cur_max_date = min(cur_date + dt.timedelta(hours=12), max_date)  # конец периода при обращении к API
    dep_list = {}  # список вылетов, попадающих в период
    arrival_list = {}  # список прилётов, попадающих в период

    while cur_date < max_date:  # цикл по периодам длиной 12 часов
        cur_date_str = cur_date.strftime('%Y-%m-%dT%H:%M')
        cur_max_date_str = cur_max_date.strftime('%Y-%m-%dT%H:%M')

        url = f'{BASE_URL}{base_airport}/{cur_date_str}/{cur_max_date_str}'

        headers = {
            'x-rapidapi-key': "3da284b1d1msh67a5ab95be38457p11c19bjsn0baca219ccd2",
            'x-rapidapi-host': "aerodatabox.p.rapidapi.com"
        }
        querystring = {"withLeg": "true", "withCancelled": "false", "withCodeshared": "true",
                       "withCargo": "false", "withPrivate": "false"}

        response = requests.request("GET", url, headers=headers, params=querystring)  # дёрнули API
        if response.status_code != 200:
            print(response)
            return 'Что-то пошло не так'

        resp_json = response.json()
        resp_departure = resp_json['departures']
        resp_arrival = resp_json['arrivals']

        for one_flight in resp_departure:  # цикл по всем вылетам в текущем 12-и часовом интервале
            try:
                icao: str = one_flight['arrival']['airport']['icao']
            except KeyError:  # не нашли код аэропорта для рейса. Игнорируем.
                continue
            if icao not in dep_list:  # такого аэропорта в списке ещё нет
                dep_list[icao] = []

            new_item = parse_one_flight(one_flight)
            # print(new_item['time_departure'].replace(tzinfo=None))
            dep_list[icao].append(new_item)

        for one_flight in resp_arrival: # цикл по всем прилётам в текущем 12-и часовом интервале
            try:
                icao: str = one_flight['departure']['airport']['icao']
            except KeyError:  # не нашли код аэропорта для рейса. Игнорируем.
                continue
            if icao not in arrival_list:  # такого аэропорта в списке ещё нет
                arrival_list[icao] = []
            new_item = parse_one_flight(one_flight)

            # print(new_item['time_departure'].replace(tzinfo=None))
            arrival_list[icao].append(new_item)

        cur_date = cur_max_date + dt.timedelta(minutes=1)  # начало следующего периода = конец текущего + 1 минута
        cur_max_date = min(cur_date + dt.timedelta(hours=12, minutes=-1), max_date)

    # сортируем вылеты из базового аэропорта по каждому пункту назначения в порядке возрастания времени прибытия
    # в пункт путешествия (самый ранний вылет вначале)
    for icao in dep_list:
        dep_list[icao].sort(key=lambda flight: flight['time_arrival'])

    # сортируем возвращения в базовый аэропорт по каждому пункту назначения в порядке убывания времени вылета
    # из пункта путешествия (самый поздний вылет в начале)
    for icao in arrival_list:
        arrival_list[icao].sort(key=lambda flight: flight['time_departure'], reverse=True)

    # финальный рывок - отбираем аэропорты и рейсы, которые подпадают под ограничения.
    ret_data = []  # итоговый объект
    for icao in dep_list:
        minimum_time_arrival = dep_list[icao][0]['time_arrival']
        try:
            maximum_time_departure = arrival_list[icao][0]['time_departure']
        except KeyError:  # вылет есть, возврата нет
            continue
        maximum_stay = maximum_time_departure - minimum_time_arrival
        print(f'{icao=} {minimum_time_arrival=:%Y-%m-%d %H:%M:%S}   {maximum_time_departure=:%Y-%m-%d %H:%M:%S}  {maximum_stay=} {min_stay=}')
        if maximum_stay < min_stay:
            print(f'Хрен вам, а не {icao}')
            continue
        one_airport = {}
        one_airport['destination_airport_icao'] = icao
        one_airport['destination_airport_name'] = 'ToDo: airport name'
        one_airport['maximum_stay'] = round(maximum_stay.total_seconds()/3600)

        one_airport['flight_list_outbound'] = []
        for one_flight in dep_list[icao]:
            if one_flight['time_arrival'] + min_stay < maximum_time_departure:
                one_airport['flight_list_outbound'].append(one_flight)

        one_airport['flight_list_inbound'] = []
        for one_flight in arrival_list[icao]:
            if one_flight['time_departure'] - min_stay > minimum_time_arrival:
                one_airport['flight_list_inbound'].append(one_flight)
        ret_data.append(one_airport)
    return json.dumps(ret_data, default=date_convert_json)

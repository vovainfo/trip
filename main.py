import trip


res = trip.get_route_list(base_airport='UHWW', minimum_departure_date='2021-08-15T10:00',
                    maximum_return_date='2021-08-17T15:00', minimum_stay='20')

print('Всё!')
print(res)

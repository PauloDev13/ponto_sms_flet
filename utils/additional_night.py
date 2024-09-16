from datetime import datetime, timedelta, time


# FUNÇÃO QUE CALCULA SE AS HORAS TRABALHADAS COMPREENDE O PERÍODO DE 22 ÀS 05 HORAS
def additional_night_calculation(
        start_dt: datetime,
        end_dt: datetime,
        start_hs: time,
        end_hs: time
) -> bool | None:
    # Se todos os argumentos passados são diferentes de None...
    if (start_dt and start_hs) or (end_dt and end_hs):

        # # Cria os objetos datetime de entrada e saída
        # combinando data e horário ('dd/MM/yyyy H:m:s')
        entry_date = datetime.combine(start_dt, start_hs)
        exit_date = datetime.combine(end_dt, end_hs)

        # Se a saída é no dia seguinte e a hora de saída é
        # menor que a de entrada, ajustamos a data de saída
        if exit_date < entry_date:
            exit_date += timedelta(days=1)

        # Definindo o período noturno (das 22:00 às 05:00 do dia seguinte)
        start_night_work = entry_date.replace(hour=22, minute=0, second=0)
        end_night_work = exit_date.replace(hour=5, minute=0, second=0) + timedelta(days=1)

        # Verificar se há interseção entre o período de trabalho e o período noturno
        return entry_date < end_night_work and exit_date > start_night_work

    else:
        return None
    #
    # # if start_day_night < end_day_night:
    # #     hours_worked = end_day_night - start_day_night
    # #     total_hours_worked = hours_worked.seconds // 3600
    # #     total_minutes_worked = (hours_worked.seconds % 3600) // 60
    # #
    # #     return total_hours_worked, total_minutes_worked
    # # else:
    # #     return 0, 0

import csv
import re
from abc import ABC
from enum import IntEnum
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import pandas as pd


def check_building_pattern(pattern: str, fns_str: str, kassa_str: str) -> bool | None:
    match = re.search(pattern, fns_str)
    if not match:
        return None
    first_part, second_part = match.groups()
    flexible_pattern = rf"{first_part}\W*{second_part}"
    return bool(re.search(flexible_pattern, kassa_str))


class FNSCellEnum(IntEnum):
    Index = 0
    # Country = 1
    # RegionCode = 2
    Region = 3
    # Region2 = 4
    # Area = 4
    City = 6
    Street = 8
    Building = 10
    Building1 = 11

    @staticmethod
    def list() -> list:
        return sorted(list(map(lambda c: c.value, FNSCellEnum)), reverse=True)


stop_list = [
    "ал.",
    "б.",
    "б-р",
    "влд",
    "влд.",
    "влад.",
    "г",
    "г.",
    "г-к",
    "г.о.",
    "г-ж",
    "город",
    "гп",
    "д",
    "д.",
    "двлд.",
    "дп",
    "зд",
    "зд.",
    "им",
    "им.",
    "имени",
    "к.",
    "кв-л",
    "км",
    "комната",
    "кп",
    "литер",
    "литера",
    "мкр",
    "н.п.",
    "наб",
    "п",
    "п.",
    "п н.п.",
    "пгт",
    "помещ.",
    "помещение",
    "проезд",
    "пр-кт",
    "рп",
    "пер",
    "пл",
    "пр-д",
    "с",
    "сети",
    "сл",
    "см",
    "соор.",
    "стр",
    "стр.",
    "ст-ца",
    "тракт",
    "ул",
    "улично-дорожн.сети",
    "ш",
    "ш.",
    "шоссе",
    "элем.",
]


def remove_stop_words(address: str) -> str:
    # класс преобразует и убирает "лишние" элементы из сегмента адреса на кассе
    words = address.split()
    filtered_words = [word.strip() for word in words if word not in stop_list]
    return " ".join(filtered_words)


class CSVFile(ABC):
    filename: str
    delimiter: str = ";"
    encoding: str = "utf-8-sig"
    kkt_field_name: str
    address_field_name: str
    split_address: bool = False

    def __init__(self):
        print(f"Working with {self.__class__.__name__}")
        self.data = {}
        with open(self.filename, encoding=self.encoding) as file:
            csv_file = csv.DictReader(file, delimiter=self.delimiter)
            for row in csv_file:
                address = row[self.address_field_name].lower()
                if self.split_address:
                    address = address.split(",")
                self.data[row[self.kkt_field_name]] = address


class FNSFile(CSVFile):
    label = "FNS"
    Tk().withdraw()
    filename = askopenfilename()
    address_field_name = "Адрес места установки"
    kkt_field_name = "Регистрационный номер"
    split_address = True


class KASSAFile(CSVFile):
    Tk().withdraw()
    filename = askopenfilename()
    delimiter = ";"
    address_field_name = "Адрес расчетов"
    kkt_field_name = "Регистрационный номер ККТ"


fns_file = FNSFile()
kassa_file = KASSAFile()


def main():
    pattern = r"\b(\d{6})\b"
    i = 0
    errors_list = []
    for kkt, address_list in fns_file.data.items():
        if kass_addr := kassa_file.data.get(kkt):
            alarms = []
            indx = ""
            addr = ""
            err = "отсутствует"
            error_dict = {
                "Регистрационный номер": kkt,
                "Адрес из ФНС": ",".join(address_list),
                "Адрес из ОФД": kass_addr,
                "Ошибка": err,
                "Ошибка в Индексе": indx,
                "Ошибка в адресе": [],
            }
            for idx in FNSCellEnum.list():
                is_city = idx == FNSCellEnum.City.value
                is_region = idx == FNSCellEnum.Region.value
                # is_street = idx == FNSCellEnum.Street.value
                is_building = idx == FNSCellEnum.Building.value
                address_el = address_list[idx]
                empty_city = is_city and not address_el
                if (empty_city and is_region) or not is_region:
                    alarm = True
                    if is_building:
                        fns_building_letter_pattern = r"(\d+)([A-Za-zА-Яа-я])"  # r"(\d+)([A-Za-zА-Яа-я])|(\d+)\-([A-Za-zА-Яа-я])|(\d+) ([A-Za-zА-Яа-я])"
                        fns_building_number_pattern = r"(d+)\/(\d+)"
                        if check_building_pattern(
                            fns_building_letter_pattern, address_el, kass_addr
                        ) or check_building_pattern(
                            fns_building_number_pattern, address_el, kass_addr
                        ):
                            alarm = False
                    if (
                        alarm
                        and address_el
                        and remove_stop_words(address_el) not in kass_addr
                    ):
                        alarms.append(f"{address_el}")
            if alarms:
                err = "есть"
                for alarm in alarms:
                    error_dict["Ошибка"] = err
                    if re.match(pattern, alarm):
                        error_dict["Ошибка в Индексе"] = alarm
                    else:
                        error_dict["Ошибка в адресе"].append(alarm)
                i += 1
                # print(f"Alarms ({i})! {err}, {kkt}, {kass_addr}", alarms)
            errors_list.append(error_dict)
    df = pd.DataFrame(errors_list)
    df.to_excel("errors.xlsx", index=False)


main()


# реализовать преобразование раздела с номерами домов в адресах касс, чтобы убрать лишние знаки в значении
# проверить 0004503506012940, 0003083648012256, не совпадают знаки, хотя все верно указано
# проверить 0002990049042613, 0002979220027677, не применились исключения
# проверить 0006201933051844 адрес верный, но выдает ошибку на микрорайон
# Посчитать количество действительных ошибок в адресе
# Создать вкладки с наименованиями клиентов
# проверить 0007588356015158 на факт появления адреса
# проверить 0007588307052868 на факт поялвения адреса и точности в поиске
# по Фамилии проверить статус касс с неверными адресами (полными), проверить статус в Claim, собрать и передать данные для дальнейшего анализа

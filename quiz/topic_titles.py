"""Modul va mavzu nomlari (ma'ruzalarning titul sahifasidan olingan).

Import paytida Excel fayl nomining boshidagi kod ("1.1", "10.4") shu ro'yxat bilan bog'lanadi.
Nomlarni keyinchalik admin paneldan ham o'zgartirish mumkin.
"""

EXAM_MODULE = 0  # "Tushgan testlar" — bosh sahifada mavzulardan alohida, tepada ko'rsatiladi

MODULES = {
    0: "Tushgan testlar",
    1: "Ta’lim menejmenti",
    2: "Ta’lim tashkilotini rivojlantirish va o‘quv-tarbiya jarayonini boshqarish",
    3: "Pedagoglarning kasbiy rivojlanishi va metodik xizmat",
    4: "Inson resurslarini boshqarish",
    5: "Maktabgacha ta’lim tashkilotlarida ijro intizomi",
    6: "Jamoatchilik va ota-onalar bilan o‘zaro hamkorlik",
    7: "Boshqaruv va ta’lim jarayonlarining raqamli texnologiyalari",
    8: "Bolalar salomatligi va sog‘lom ovqatlantirish",
    9: "Milliy tarbiya va milliy g‘oyaning o‘rni",
    10: "Moliyaviy menejment",
}

TOPICS = {
    "0.1": "2026-yil sentabrda tushgan testlar",
    "1.1": "Maktabgacha ta’limni boshqarish strategiyasi",
    "1.2": "Maktabgacha ta’limda boshqaruv psixologiyasi",
    "1.3": "Muammolarga yechim topish va qarorlarni qabul qilish",
    "1.4": "Maktabgacha ta’limda time menejmenti",
    "1.5": "Kollegial boshqaruv organlari faoliyatini tashkil etish",
    "2.1": "STEAM texnologiyasining asosiy tamoyillari",
    "2.2": "Davlat talablari va Davlat dasturini amaliyotga tatbiq etish",
    "2.3": "Milliy va xalqaro darajada baholash tizimlari",
    "2.4": "Korrupsiyaviy xavf-xatarlarni aniqlash va bartaraf etish",
    "2.5": "Maktabgacha ta’lim tashkilotida rahbar ma’naviyati",
    "2.6": "Bolalar xavfsizligining huquqiy asoslari va zo‘ravonlikning oldini olish",
    "3.1": "Pedagog xodimlarning kasbiy rivojlanishini tashkil etish",
    "3.2": "Uzluksiz metodik xizmatni tashkil etish",
    "3.3": "Uzluksiz kasbiy rivojlanish bo‘yicha ilg‘or xorijiy tajribalar",
    "4.1": "Inson resurslaridan samarali foydalanish va mehnat unumdorligini baholash",
    "4.2": "Kadrlar zaxirasini rejalashtirish va barqaror rivojlantirish",
    "4.3": "Jamoada sog‘lom psixologik muhitni tashkil etishda rahbarning roli",
    "5.1": "Ta’lim tashkilotida boshqaruvning me’yoriy-huquqiy asoslari",
    "5.2": "Ish yuritish va ijro intizomi",
    "5.3": "Mehnat munosabatlari va mehnat qonunchiligi",
    "6.1": "Ota-onalar, jamoatchilik va tashkilotlar bilan hamkorlik tartibi",
    "6.2": "Davlat va jamoat tashkilotlari bilan hamkorlikni tashkil etish",
    "6.3": "Maktabgacha ta’lim tashkiloti va maktab hamkorligi",
    "7.1": "Raqamli texnologiyalar va sun’iy intellektdan foydalanish",
    "7.2": "“Uzluksiz kasbiy ta’lim” elektron platformasi",
    "7.3": "bbit.uz va nodavlat-bog‘cha.uz boshqaruv platformalari",
    "7.4": "Tarbiyalanuvchilar va ota-onalar uchun ta’limiy platformalar",
    "8.1": "Ovqatlantirishni tashkil etish va monitoring olib borish",
    "8.2": "Oziq-ovqat mahsulotlarini baholash va xavflarni boshqarish",
    "9.1": "Milliy tarbiya va vatanparvarlik ruhida tarbiyalash",
    "9.2": "Tarbiyalanuvchilarda qadriyatlar tizimini shakllantirish",
    "9.3": "Rahbar nutqi va muloqot madaniyati",
    "10.1": "Moliyaviy munosabatlarning huquqiy asoslari",
    "10.2": "Inventarizatsiya va shartnomaviy munosabatlar",
    "10.3": "Budjet va budjetdan tashqari mablag‘lar",
    "10.4": "Moliyaviy hisobotlarni tuzish va taqdim qilish",
}

# Kuran Öğrenme Uygulaması

Bu proje, aralıklı tekrar (spaced repetition) yöntemini kullanarak Kuran öğrenmeyi kolaylaştıran bir web uygulamasıdır. Uygulama, API'den çekilen Kuran verileri üzerinde çalışarak kullanıcıların ayetleri düzenli aralıklarla tekrar etmelerini sağlar.

## Özellikler

- Kuran ayetlerini API'den çekme ve veritabanında saklama
- Aralıklı tekrar algoritması ile kişiselleştirilmiş öğrenme planı
- Kullanıcı hesapları ve ilerleme takibi
- Ayet ezber ve anlama çalışmaları
- İstatistikler ve ilerleme grafikleri
- Responsive tasarım (Tailwind CSS ile)

## Teknolojiler

- **Backend**: Python, Django, Django REST Framework
- **Frontend**: HTML, JavaScript, Tailwind CSS
- **Veritabanı**: PostgreSQL
- **API**: Kuran verileri için harici API entegrasyonu

## Kurulum

### Gereksinimler

- Python 3.8+
- pip
- virtualenv (önerilen)
- PostgreSQL

### Adımlar

1. Repoyu klonlayın:
   ```
   git clone https://github.com/kullanici/kuran-ogrenme-uygulamasi.git
   cd kuran-ogrenme-uygulamasi
   ```

2. Sanal ortam oluşturun ve aktifleştirin:
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # veya
   venv\Scripts\activate  # Windows
   ```

3. Bağımlılıkları yükleyin:
   ```
   pip install -r requirements.txt
   ```

4. Veritabanını oluşturun:
   ```
   python manage.py migrate
   ```

5. Geliştirme sunucusunu başlatın:
   ```
   python manage.py runserver
   ```

6. Tarayıcınızda `http://127.0.0.1:8000` adresine gidin.

## Proje Yapısı

```
kuran_ogrenme/
├── manage.py
├── kuran_project/          # Ana proje klasörü
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── users/                  # Kullanıcı yönetimi uygulaması
│   ├── models.py
│   ├── views.py
│   └── ...
├── quran/                  # Kuran verileri uygulaması
│   ├── models.py
│   ├── views.py
│   ├── api.py
│   └── ...
├── repetition/             # Aralıklı tekrar uygulaması
│   ├── models.py
│   ├── views.py
│   ├── algorithm.py
│   └── ...
└── templates/              # HTML şablonları
    ├── base.html
    ├── home.html
    └── ...
```

## Aralıklı Tekrar Algoritması

Uygulama, SM-2 (SuperMemo 2) algoritmasının bir varyasyonunu kullanarak kullanıcının her ayet için tekrar zamanlamasını belirler. Algoritma şu faktörleri dikkate alır:

- Kullanıcının ayeti ne kadar iyi bildiği (1-5 arası derecelendirme)
- Son tekrardan bu yana geçen süre
- Ayetin zorluk derecesi

## Katkıda Bulunma

Projeye katkıda bulunmak istiyorsanız:

1. Bu repoyu fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some amazing feature'`)
4. Branch'inize push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır. 
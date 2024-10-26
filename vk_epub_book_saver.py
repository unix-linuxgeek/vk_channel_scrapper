import os
import time
import vk_api
import shutil
import vk_token
import requests
from ebooklib import epub
from datetime import datetime

token = vk_token.token_id
vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()

MESSAGES_COUNT = 100
PEER_ID = 'here should be your channel id'  # Замените на ID группового чата (peer_id)
FILE_NAME = input("Введите имя файла, в который будет сохранена переписка из группового чата ВК:   ")
FILE_NAME += ".epub"


def get_group_messages(peer_id, messages_count=100, offset=0):
    response = vk.messages.getHistory(peer_id=peer_id, count=messages_count, offset=offset)
    return response


def download_photo(attachment, timestamp, folder):
    if attachment['type'] == 'photo':
        photo = attachment['photo']
        url = photo['orig_photo']['url']
        file_ext = url.split('?')[0].split('.')[-1]
        file_name = f"{photo['id']}_{timestamp}.{file_ext}"
        img_path = os.path.join(folder, file_name)
        img_data = requests.get(url).content
        with open(img_path, 'wb') as handler:
            handler.write(img_data)
        print(f"Сохранено изображение: {img_path}")
        return img_path


def extract_messages(messages):
    message_list = []
    messages = reversed(messages['items'])  # Разворачиваем список сообщений
    for message in messages:
        img_paths = []
        timestamp = message.get('date')
        readable_date = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S %d-%m-%Y')
        text = message.get('text', '').strip()
        if 'attachments' in message:
            for attachment in message['attachments']:
                img_path = download_photo(attachment, timestamp, folder='img')
                if img_path:
                    img_paths.append(img_path)

        message_list.append({
            'id': message['id'],
            'text': text,
            'img_paths': img_paths,
            'date': readable_date,
            'sender_name': message.get('from_id')  # Получаем ID отправителя
        })
    
    return message_list


def create_epub_file(file_name):
    """Создаёт новый EPUB-файл."""
    book = epub.EpubBook()
    book.set_title(file_name)
    book.set_language("ru")
    book.add_author("Laplas Courses")  # Укажите автора, если нужно
    book.add_item(epub.EpubNcx())
    style = """BODY {
    text-align: justify;
    line-height: 1.6;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.1em;
    margin: 1em;
    padding: 0;
    color: #333;
}

h1, h2, h3 {
    font-family: Georgia, Times New Roman, sans-serif;
    color: #2c3e50;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    text-align: left;
}

h1 { font-size: 2em; font-weight: bold; }
h2 { font-size: 1.5em; font-weight: bold; }
h3 { font-size: 1.2em; font-weight: normal; }

/* Стиль для изображений */
img {
    max-width: 100%;       /* Ограничивает максимальную ширину изображения до 100% ширины контейнера */
    max-height: 100%;      /* Ограничивает максимальную высоту изображения до 100% высоты контейнера */
    height: auto;          /* Автоматически подстраивает высоту, сохраняя соотношение сторон */
    width: auto;           /* Автоматически подстраивает ширину, сохраняя пропорции */
    display: block;        /* Делает изображение блочным элементом, чтобы убрать лишние отступы вокруг */
    margin: 1em auto;      /* Устанавливает отступ в 1em сверху и снизу, а по бокам выравнивает по центру */
    
}

/* Стиль для контейнера изображений */
.img-container {
    display: flex;             /* Применяет Flexbox для контейнера, что позволяет легко центрировать содержимое */
    justify-content: center;   /* Центрирует изображение по горизонтали внутри контейнера */
    align-items: center;       /* Центрирует изображение по вертикали внутри контейнера */
    width: 100%;               /* Устанавливает ширину контейнера на 100% от родительского элемента */
    height: 100vh;             /* Устанавливает высоту контейнера на 100% от высоты окна браузера */
    flex-grow: 1;              /* Элементы растягиваются, занимая доступное пространство */
}


a {
    color: #3498db;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
    color: #2980b9;
}

.meta-info {
    font-size: 0.9em;
    color: #888;
    margin-bottom: 1em;
}

p { margin: 0 0 1em 0; }

ul, ol {
    margin-left: 1.5em;
    padding-left: 1em;
}

li {
    margin-bottom: 0.5em;
}

blockquote {
    border-left: 4px solid #ccc;
    padding-left: 1em;
    margin-left: 0;
    color: #555;
    font-style: italic;
    background-color: #f9f9f9;
} """

    #'''BODY { text-align: justify;}''' оригинальный стиль
    default_css = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css",
                                content=style)
    book.add_item(default_css)

    return book, default_css


def add_chapter_to_epub(book, style, message, message_number):
    """Добавляет новую главу в существующий EPUB-файл."""

    # Создаём новую главу
    chapter = epub.EpubHtml(title=f"Задача №{message_number}",
                            file_name=f"chapter_{message['id']}.xhtml",
                            lang='ru')

    txt = ''
    img_html = ''  # Для хранения HTML с изображениями
    if message['text']:
        txt = message['text']

    # Добавляем изображения, если они есть
    if message['img_paths']:
        for idx, img_path in enumerate(message['img_paths']):
            # Чтение содержимого изображения
            with open(img_path, 'rb') as img_file:
                image_content = img_file.read()

            # Создание объекта изображения для EPUB
            img = epub.EpubImage(uid=f'image_{message_number}_{idx}', # уникальный идентификатор изображения.
                                 # Включает номер сообщения и индекс изображения,
                                 # чтобы каждый файл имел уникальный идентификатор.
                                 file_name=f'static/{os.path.basename(img_path)}', #имя файла,
                                 # которое будет использоваться в EPUB. os.path.basename(img_path)
                                 # извлекает только имя файла из полного пути (например, "image.jpg"),
                                 # и оно сохраняется в директорию static внутри EPUB.
                                 media_type='image/jpeg',  # Замените на правильный формат (jpeg/gif/png)
                                 content=image_content) #это содержимое изображения, которое было прочитано из файла.

            # Добавляем изображение в книгу
            book.add_item(img)

            # Генерация HTML кода для вставки изображения
            img_html += f'<img src="static/{os.path.basename(img_path)}" alt="photo"/>'

    # Создаём HTML контент главы
    content = f'''<html>
      <head></head>
      <body>
        <h1>Задача №{message_number}</h1>
        <p>{txt}</p>
        <div class="img-container">
            {img_html}
        </div>
      </body>
    </html>'''

    # Устанавливаем контент главы и добавляем её в книгу
    chapter.set_content(content)
    book.add_item(chapter)

    # Добавляем главу в оглавление и обновляем навигацию
    book.toc.append(chapter)
    book.spine.append(chapter)


def finish_epub(book, file_name):
    # Создание стиля навигации
    nav_css_content = '''
    @namespace epub "http://www.idpf.org/2007/ops";

    body {
        font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
    }

    h2 {
         text-align: left;
         text-transform: uppercase;
         font-weight: 200;     
    }

    ol {
        list-style-type: none;
    }

    ol > li:first-child {
        margin-top: 0.3em;
    }

    nav[epub|type~='toc'] > ol > li > ol {
        list-style-type: square;
    }

    nav[epub|type~='toc'] > ol > li > ol > li {
        margin-top: 0.3em;
    }
    '''

    # Добавляем стиль навигации
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=nav_css_content)
    book.add_item(nav_css)

    # Запись книги в EPUB-файл
    epub.write_epub(file_name, book, {})
    print("epub файл успешно создан!")


def parse_all_messages(chat_id, posts_count, file_name):
    folder_name = 'img'
    if os.path.exists(folder_name):
        shutil.rmtree(folder_name)
    os.mkdir(folder_name)

    # Создаём EPUB-файл, если он не существует
    if not os.path.exists(file_name):
        book, style = create_epub_file(file_name)

    messages = get_group_messages(chat_id, posts_count, offset=0)
    total_messages = messages['count']
    if total_messages == 0:
        print("Нет сообщений для обработки.")
        return None
    print(f"Всего сообщений в переписке: {total_messages}")
    quantity_pages = total_messages // 100
    offset = quantity_pages * posts_count
    message_number = 1

    while offset >= 0:
        messages = get_group_messages(chat_id, posts_count, offset)
        if messages['items']:
            print(f"Количество полученных сообщений: {len(messages['items'])}")
            message_list = extract_messages(messages)
            for message in message_list:
                add_chapter_to_epub(book, style, message, message_number)
                print(f"Обработано сообщение: {message['id']}")
                time.sleep(0.3)  # Для предотвращения частых запросов
                message_number += 1
            offset -= posts_count
        else:
            print("Сообщений для сохранения больше нет!")
            break
    finish_epub(book, file_name)


parse_all_messages(PEER_ID, MESSAGES_COUNT, FILE_NAME)

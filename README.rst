.. image:: https://badge.fury.io/py/Flask-REST-JSONAPI.svg
    :target: https://badge.fury.io/py/Flask-REST-JSONAPI
.. image:: https://travis-ci.org/miLibris/flask-rest-jsonapi.svg
    :target: https://travis-ci.org/miLibris/flask-rest-jsonapi
.. image:: https://coveralls.io/repos/github/miLibris/flask-rest-jsonapi/badge.svg
    :target: https://coveralls.io/github/miLibris/flask-rest-jsonapi
.. image:: https://readthedocs.org/projects/flask-rest-jsonapi/badge/?version=latest
    :target: http://flask-rest-jsonapi.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status


ComboJSONAPI - это прокаченный форк библиотеки `Flask-REST-JSONAPI <https://flask-rest-jsonapi.readthedocs.io/en/latest/quickstart.html>`_
==========================================================================================================================================
В данном форке улучшено/добавлено следующее:

1.  Библиотека переведена на marshmallow=3.0.0.
2.  Улучшены фильтры. Теперь доступна глубокая фильтрация, например (см. ниже) и нам нужно выгрузить всех пользователей, у которых менеджер находится в определённой группе с названием начинающимся на `Test`:code:\, фильтр будет выглядеть следующим образом:

    .. code:: python

        filter=[{"name": "manager_id__group_id__name", "op": "ilike", "val": "Test%"}]

    - есть таблица `User`:code:\ с полями:
        - `manager_id`:code:\,  которое является "внешним" ключом к таблице `User`:code:\
        - `group_id`:code:\,  которое является "внешним" ключом к таблице `Group`:code:\
    - есть таблица `Group`:code:\ с полем:
        - `name`:code:\ - имя группы
3. Улучшены сортировки. Теперь доступна глубокая сортировка, принцип как у глубокой фильтрации
4. Добавлена десериализация/валидация значение, которые приходят для фильтров
5. Добавлена возможность для кастомных полей добавлять свой метод для создания фильтра и сортировки к БД (подробнее будет описано ниже).
6. Добавлена поддержка плагинов (`Подробнее <docs/plugins/create_plugins.rst>`_).
7. Разработан плагин **Permission** позволяющий создавать различные системы доступа к моделям и полям на выгрузку/создание/изменение/удаление (`Подробнее <docs/plugins/permission_plugin.rst>`_)
8. Разработан плагин **ApiSpecPlugin** позволяющий генерировать упрощённую автодокументацию для JSONAPI (`Подробнее <docs/plugins/api_spec_plugin.rst>`_)
9. Разработан плагин **RestfulPlugin** для библиотеки apispec внутри плагина **ApiSpecPlugin** способствующий описанию параметров в get запросах при помощью схем marshmallow (`Подробнее <docs/plugins/restful_plugin.rst>`_)
10. Разработан плагин **EventPlugin** для создания RPC, для тех случаев когда очень тяжело обойтись только JSON:API (`Подробнее <docs/plugins/event_plugin.rst>`_).
11. Разработан плагин **PostgreSqlJSONB** для возможности фильтровать и сортировать по верхним ключам в полях `JSONB`:code:\ в PostgreSQL (`Подробнее <docs/plugins/postgresql_jsonb.rst>`_).


Пример создания у кастомных полей спецефичных фильтров в запросах к БД
----------------------------------------------------------------------
Например, у нас есть тип данных `Flag`:code:\ построенный на основе работы с битами. В БД всегда будет храниться число.

.. code:: python

    from enum import Enum

    class Flag(Enum):
        null = 1
        success = 1 << 1
        in_process = 1 << 2
        error = 1 << 3

Чтобы клиент мог работать с флагами не задумываясь, как это работает за кулисами, нам нужно создать свой тип поля для
`marshmallow`:code:\, в которой реализуем сериализацию и десериализацию. Из коробки JSON:API, также не сможет работать с
таким видом данных, не фильтровать, не обновлять, не корректно выгружать, если конечно мы не зотим чтобы пользователь
сам уже разбирался с корректным предстовлением данного флага.

.. code:: python

    from enum import Enum
    from marshmallow_jsonapi import fields
    from sqlalchemy import and_, or_
    from sqlalchemy.sql.functions import GenericFunction
    from sqlalchemy import Integer


    class BitAnd(GenericFunction):
        type = Integer
        package = 'adc_custom'
        name = 'bit_and'
        identifier = 'bit_and'


    def bit_and(*args, **kwargs):
        return BitAnd(*args, **kwargs)


    class FlagField(fields.List):
        def __init__(self, *args, flags_enum=None, **kwargs):
            if flags_enum is None or not issubclass(flags_enum, Enum):
                raise ValueError("invalid attr %s" % flags_enum)
            self.flags_enum = flags_enum

            # Тип FlagField - это массив для сваггера, а элементы этого массива строки
            super().__init__(fields.String(enum=[e.name for e in self.flags_enum]), *args, **kwargs)

        @classmethod
        def _set_flag(cls, flag, add_flag):
            if add_flag:
                flag |= add_flag
            return flag

        def _deserialize(self, value, attr, data, **kwargs):
            flag = 0
            for i_flag in value:
                flag |= getattr(self.flags_enum, i_flag, 1).value
            return flag

        def _serialize(self, value, attr, obj, **kwargs):
            return [
                i_flag.name
                for i_flag in self.flags_enum
                if value & i_flag.value == i_flag.value
            ]

        def _in_sql_filter_(self, marshmallow_field, model_column, value, operator):
            """
            Создаёт фильтр для sqlalchemy с оператором in
            :param marshmallow_field: объект класса поля marshmallow
            :param model_column: объект класса поля sqlalchemy
            :param value: значения для фильтра
            :param operator: сам оператор, например: "eq", "in"...
            :return:
            """
            filters_flag = []
            for i_flag in value:
                flag = self._deserialize(0, self.flags_enum[i_flag], None, None)
                filters_flag.append(and_(flag != 0, model_column != 0, bit_and(model_column, flag) != 0))
            return or_(*filters_flag)




Автор форка: `Aleksei Nekrasov (znbiz) <https://github.com/Znbiz>`_

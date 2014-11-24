================
Reglas de Ventas
================

Configuración
=============

A través del menú Ventas> Configuración> Regla de venta, como es habitual en
Tryton se abre una nueva ventana con la lista de reglas disponibles.

Para crear una nueva regla de venta debe hacer click en el icono de nuevo y en
el formulario que se abre rellenar los siguientes campos:

  * Descripción. Una pequeña descripción de lo que hace la regla para
    identificarla.
  * Activo: Para tenerla en cuenta cuando se vayan a aplicar las reglas. Si
    está desactivado, se omite la aplicación de esta regla.
  * Detiene las comprobaciones: Esta casilla de verificación se utiliza para
    evitar que se apliquen más reglas si las condiciones de esta regla hacen
    que esta se aplique. El orden viene dado por el campo secuencia que se ve
    en la vista de lista. Para ordenar las reglas sólo hay arrastrar-soltar con
    el ratón.
  * Desde fecha y hasta fecha: Si desea que esta regla sólo se aplique en un
    determinado periodo de tiempo.
  * Tienda: Si quiere que esta regla sólo se aplique a determinada tienda, aquí
    la debe indicar.
  * Categoría de tercero: Si quiere que esta regla sólo se aplique a un
    determinado conjunto de terceros determinado por su categoría.

A continuación debe crear las condiciones que desea que se cumplan en la venta
para aplicar esta regla. Para crearlas se debe ir a la pestaña Condiciones del
formulario de la regla de venta (por defecto es el primero, o sea seguramente
ya lo verá). Por ejemplo, si quiere que esta regla se aplique a las ventas cuyo
importe sea superior a 100 €, cree una nueva condición y rellene los siguientes
campos:

  * Secuencia: No hay que poner nada, se rellena por defecto cuando se guarda.
  * Criterio: En función de los módulos instalados hay más o menos criterios.
    Los básicos son:
    + Cantidad total de productos
    + Cantidad total de productos de categoría
    + Importe sin impuestos
    + Importe total
    + Total impuestos
    + Total productos
    + El módulo sale_rule_manufacturer añade la posibilidad de filtrar por
     fabricante: Cantidad total de productos de fabricante.
    + Y el módulo sale_rule_weight añade la posibilidad de filtrar por el peso
     de la venta: Peso total.
  * Producto, Categoría de Producto, Fabricante: En función del criterio
    seleccionado se deben rellenar unos campos u otros. Por ejemplo, si se
    selecciona:
    + "Cantidad total de productos" se debe rellenar el producto,
    + "Cantidad total de productos de categoría" se debe rellenar la categoría
     del producto,
    + "Cantidad total de productos de fabricante" se debe rellenar el
     fabricante.
  * Condición: A continuación se debe poner la condición. Hay las siguientes
    posibilidades:
    + Igual a
    + Diferente de
    + Más pequeño que
    + Menor o igual que
    + Mayor que
    + Mayor o igual que
    + Múltiplo de
    + No múltiplo de
  * Cantidad: por último se indicará la cantidad con la que se ha de comparar
    el criterio seleccionado.
  * Detiene resto de comprobaciones: Si quiere que ignore el resto de
    condiciones si se cumple la misma.

Para el ejemplo indicado anteriormente de ventas del importe, sea superior a
100 € seleccionaríamos:
  * Criterio: Importe total
  * Condición: mayor o igual que
  * Cantidad: 100

Fíjese que sobre el campo Condiciones, hay otro campo de tipo selección
denominado Cuantificador. Este campo sirve para decirle a Tryton si desea que
esta regla se aplique a las ventas cuando se cumpla alguna de las condiciones o
es necesario que se cumplan todas las condiciones para poderse aplicar.

Finalmente queda crear las acciones correspondientes a ejecutar cuando se
cumplen todas o algunas condiciones de esta regla. Para crearlas tiene que
hacer clic en la pestaña Acciones y sobre el icono nueva acción que se
encuentra arriba a la derecha. Los campos a rellenar son los siguientes:

  * Secuencia: No hay que hacer nada, se rellena por defecto.
  * Acción: Hay cuatro posibilidades:
    + % De descuento en subtotal: Esta acción crea una nueva línea a la venta
      con un tanto por ciento de descuento sobre el subtotal de la venta.
    + Importe fijo en subtotal: Igual que el anterior pero con un importe fijo
      en vez de un tanto por ciento.
    + Obtenga X productos gratis: Añade una línea a la venta con X productos a
      precio 0 €
    + Detener la venta: Si se cumplen las condiciones de esta regla, esta
      acción no permite cambiar venta a estado presupuesto.
  * Producto: Es el producto que se añade a la nueva línea de venta. En el caso
    de los descuentos se debería añadir el producto descuento, en el caso del
    producto gratis, el producto que se tiene que regalar.
  * Cantidad: Es la cantidad que afecta a la acción. En el caso del % de
    descuento, se debe introducir el tanto por ciento, en el caso del importe
    fijo, la cantidad en € y en el caso del producto gratis, el número de
    productos.
  * Comentario: El texto que se escriba en este campo será la descripción que
    aparezca en la nueva línea de venta.

Funcionamiento
==============

Cuando cree una nueva venta, verá un botón a la izquierda del botón cancelar
que le permite aplicar la regla sin pasarla a estado presupuesto. Además,
cuando la venta cambie de estado borrador a presupuesto se aplican todas las
reglas que cumplan las condiciones.

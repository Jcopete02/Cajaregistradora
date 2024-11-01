import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

class CajaRegistradoraDB:
    def __init__(self, db_name="caja_registradora.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.crear_tablas()
        self.agregar_productos_iniciales()

    def crear_tablas(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY, nombre TEXT UNIQUE, precio REAL, stock INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS historial_ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, producto_id INTEGER,
            cantidad INTEGER, total REAL, fecha TEXT,
            FOREIGN KEY (producto_id) REFERENCES productos(id))''')
        self.connection.commit()

    def agregar_productos_iniciales(self):
        productos_iniciales = [(1, "Manzana", 1000, 50), (2, "Banana", 500, 100), 
                               (3, "Naranja", 750, 80), (4, "Uva", 2000, 60)]
        self.cursor.executemany('INSERT OR REPLACE INTO productos (id, nombre, precio, stock) VALUES (?, ?, ?, ?)', 
                                 productos_iniciales)
        self.connection.commit()

    def mostrar_productos(self):
        self.cursor.execute("SELECT id, nombre, precio, stock FROM productos")
        for producto in self.cursor.fetchall():
            print(f"ID: {producto[0]}, Nombre: {producto[1]}, Valor: ${producto[2]:,} COP, Stock: {producto[3]}")

    def ingresar_productos(self, productos):
        total_compra = 0
        detalles_compra = []
        for producto_id, cantidad in productos.items():
            self.cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE id = ?", (producto_id,))
            producto = self.cursor.fetchone()
            if producto and producto[3] >= cantidad:  # Verifica el stock
                total = producto[2] * cantidad
                total_compra += total
                detalles_compra.append((producto[1], cantidad, producto[2], total))  # Nombre, cantidad, precio, total
                self.cursor.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", 
                                    (cantidad, producto_id))
                self.cursor.execute("INSERT INTO historial_ventas (producto_id, cantidad, total, fecha) VALUES (?, ?, ?, ?)", 
                                    (producto_id, cantidad, total, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            else:
                print(f"Producto ID '{producto_id}' no encontrado o sin suficiente stock.")
        self.connection.commit()
        print(f"Compra realizada con éxito. Total: ${total_compra:,} COP")
        self.generar_recibo(detalles_compra, total_compra)

    def generar_recibo(self, detalles_compra, total_compra):
        # Generar PDF
        c = canvas.Canvas("recibo_compra.pdf", pagesize=letter)
        c.drawString(100, 750, "---- Recibo de Compra ----")
        c.drawString(100, 730, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        y = 710
        for nombre, cantidad, precio, total in detalles_compra:
            c.drawString(100, y, f"Producto: {nombre}, Cantidad: {cantidad}, Precio: ${precio:,} COP, Total: ${total:,} COP")
            y -= 20
        
        c.drawString(100, y, f"Total de la compra: ${total_compra:,} COP")
        c.drawString(100, y - 20, "Gracias por su compra!")
        c.save()
        print("Recibo generado: recibo_compra.pdf")

    def devolver_producto(self, producto_id, cantidad):
        self.cursor.execute("SELECT stock, precio FROM productos WHERE id = ?", (producto_id,))
        producto = self.cursor.fetchone()
        if producto:
            stock, precio = producto
            self.cursor.execute('''SELECT id, cantidad FROM historial_ventas WHERE producto_id = ? ORDER BY id DESC LIMIT 1''', 
                                (producto_id,))
            venta = self.cursor.fetchone()
            if venta and venta[1] >= cantidad:
                self.cursor.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", 
                                    (cantidad, producto_id))
                nueva_cantidad = venta[1] - cantidad
                if nueva_cantidad > 0:
                    self.cursor.execute("UPDATE historial_ventas SET cantidad = ?, total = ? WHERE id = ?", 
                                        (nueva_cantidad, nueva_cantidad * precio, venta[0]))
                else:
                    self.cursor.execute("DELETE FROM historial_ventas WHERE id = ?", (venta[0],))
                self.connection.commit()
                print(f"Devolución de ID '{producto_id}' ({cantidad} unidades) realizada.")
            else:
                print("No hay suficiente registro de ventas para devolver.")
        else:
            print("Producto no encontrado.")

    def mostrar_historial_ventas(self):
        self.cursor.execute('''SELECT productos.nombre, historial_ventas.cantidad, historial_ventas.total 
                               FROM historial_ventas JOIN productos ON historial_ventas.producto_id = productos.id''')
        ventas = self.cursor.fetchall()
        if ventas:
            print("Historial de ventas:")
            for venta in ventas:
                print(f"Producto: {venta[0]}, Cantidad: {venta[1]}, Total: ${venta[2]:,} COP")
        else:
            print("No hay ventas registradas.")

    def cerrar(self):
        self.connection.close()

def menu():
    caja = CajaRegistradoraDB()
    while True:
        print("\n---- Caja Registradora ----")
        print("1. Mostrar productos\n2. Ingresar productos para venta\n3. Mostrar historial de ventas\n4. Devolver producto\n5. Salir")
        opcion = input("Elige una opción: ")
        if opcion == "1":
            caja.mostrar_productos()
        elif opcion == "2":
            caja.mostrar_productos()
            productos = {}
            print("Ingresa los productos (deja el ID vacío para finalizar):")
            while True:
                producto_id = input("ID del producto: ")
                if not producto_id:
                    break
                try:
                    cantidad = int(input("Cantidad a vender: "))
                    if cantidad <= 0:
                        print("La cantidad debe ser mayor que cero.")
                        continue
                    productos[int(producto_id)] = cantidad
                except ValueError:
                    print("Por favor, ingresa un número válido para la cantidad.")
                    continue
            if productos:
                caja.ingresar_productos(productos)
            else:
                print("No se ingresaron productos para la venta.")
        elif opcion == "3":
            caja.mostrar_historial_ventas()
        elif opcion == "4":
            caja.mostrar_productos()
            try:
                producto_id = int(input("ID del producto a devolver: "))
                cantidad = int(input("Cantidad a devolver: "))
                if cantidad <= 0:
                    print("La cantidad debe ser mayor que cero.")
                    continue
                caja.devolver_producto(producto_id, cantidad)
            except ValueError:
                print("Por favor, ingresa un número válido.")
        elif opcion == "5":
            caja.cerrar()
            break
        else:
            print("Opción no válida.")

if __name__ == "__main__":
    menu()

"""
MIGLIORIE:
    
La funzione init esegue un ciclo attraverso tutte le rotte  ogni volta che viene chiamata e
potrebbe diventare lento se ci sono molte rotte quindi servirebbe mantenere una copia locale dei flag deprecated 
delle rotte per evitare di dover ciclare attraverso tutte le rotte ogni volta. E tale copia dovrà essere usata anche 
dalla funzione deprecate_route per renderla più veloce
"""

from fastapi import FastAPI, APIRouter
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.exc import IntegrityError
from dipendency import *
from database import Route

"""
# Modello dei dati

class Route(Base):
    __tablename__ = "routes"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(50))
    path = Column(String(50), nullable=False)
    description = Column(String(100), nullable=False)
    desprecated = Column(Boolean, nullable=False, default=True)  
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
"""

# Creazione della sessione del database
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

# Creazione dell'applicazione FastAPI
app = FastAPI()

# Creazione dei tre router APIRouter
router1 = APIRouter()
router2 = APIRouter()
router3 = APIRouter()

@router1.get("/hello1")
def hello1(session: Session):
    # Imposta il flag deprecated a True per la rotta "/hello1"
    deprecate_route([hello1], "/hello1", True, session)
    return {"message": "Hello from Router1!"}

@app.get("/myroute")
def my_route(session: Session):
    if is_myself_deprecated(my_route.__wrapped__):
        return {"message": "This route is deprecated."}
    else:
        return {"message": "This route is active."}

# Funzione per verificare se la funzione è marcata come deprecated
def is_myself_deprecated(func) -> bool:
    """
    Verifica se la funzione ha il flag 'deprecated' impostato a True nel decoratore.
    """
    return func.__dict__.get("deprecated", False)

def deprecate_route(routes, route_name: str, flag: bool, session: Session):
    """
    Imposta il flag 'deprecated' del decoratore di una rotta a True o False in base al valore 
    del flag passato e salva l'informazione sul database.
    """
    try:
        db_route = session.query(Route).filter_by(path=route_name).first()
        if db_route:
            if db_route.deprecated != flag:
                with session.begin():
                    db_route.deprecated = flag
                    session.commit()
                    for route in routes:
                        if route.path == route_name:
                            route.deprecated = flag
                            break
        else:
            new_route = Route(path=route_name, active=True, deprecated=flag)
            with session.begin():
                session.add(new_route)
                session.commit()
                for route in routes:
                    if route.path == route_name:
                        route.deprecated = flag
                        break
    except IntegrityError:
        print(f"Error: Failed to update database for route {route_name}")


# Funzione di inizializzazione dell'applicazione
def init(app: FastAPI, session: Session):
    """
    Inizializza l'applicazione impostando i flag deprecated delle rotte in base al contenuto della tabella 'routes' del database.
    """
    try:
        # Query al database per recuperare tutte le rotte attive
        active_routes: List[Route] = session.query(Route).filter(Route.active.is_(True)).all()

        # Ciclo sulle rotte attive e imposta il flag deprecated in base al valore del campo 'deprecated' del database
        for active_route in active_routes:
            route_name = active_route.path
            route_exists = False

            # Cerca la rotta corrispondente nell'applicazione principale
            for route in app.routes:
                if route.path == route_name:
                    route_exists = True
                    # Imposta il flag deprecated in base al valore del campo 'deprecated' del database
                    deprecate_route([route], route_name, active_route.deprecated, session)

            # Ciclo sui router montati sull'applicazione principale
            for router in app.routers:
                # Cerca la rotta corrispondente nel router
                for route in router.routes:
                    if route.path == route_name:
                        route_exists = True
                        # Imposta il flag deprecated in base al valore del campo 'deprecated' del database
                        deprecate_route([route], route_name, active_route.deprecated, session)

            # Se la rotta non esiste né nell'applicazione principale né nei router montati su di essa, emette un messaggio di warning
            if not route_exists:
                print(f"Warning: Route {route_name} not found in the application or any mounted router.")
    except Exception as e:
        print(f"Error occurred during initialization: {e}")
    finally:
        session.close()

"""
# Versione che usa app.url_path_for() 

def init(app: FastAPI, session: Session):
    try:
        # Query al database per recuperare tutte le rotte attive
        active_routes: List[Route] = session.query(Route).filter(Route.active.is_(True)).all()

        # Ciclo sulle rotte attive e imposta il flag deprecated in base al valore del campo 'deprecated' del database
        for active_route in active_routes:
            route_name = active_route.path
            route_exists = False

            # Cerca la rotta corrispondente nell'applicazione principale e nei router montati su di essa
            for route in app.routes + sum([router.routes for router in app.routers], []):
                if route.path == route_name:
                    route_exists = True
                    # Imposta il flag deprecated in base al valore del campo 'deprecated' del database
                    deprecate_route([route], route_name, active_route.deprecated, session)

                    # Aggiorna la lista dei router montati sulla rotta, se presente
                    if isinstance(route, APIRoute):
                        for router in app.routers:
                            if router.routes and router.routes[0].path == route.path:
                                route.scope = router.scope
                                break

            # Se la rotta non esiste né nell'applicazione principale né nei router montati su di essa, emette un messaggio di warning
            if not route_exists:
                print(f"Warning: Route {route_name} not found in the application or any mounted router.")
    except Exception as e:
        print(f"Error occurred during initialization: {e}")
    finally:
        session.close()

"""

def refresh(app: FastAPI, session: Session):
    """
    Aggiorna l'applicazione verificando le rotte nel database e aggiornando 
    i flag dei decoratori delle rotte che hanno subito un cambiamento nel db a runtime.
    """
    try:
        # Query al database per recuperare tutte le rotte attive
        active_routes: List[Route] = session.query(Route).filter(Route.active.is_(True)).all()

        # Ciclo sulle rotte attive e imposta il flag deprecated in base al valore del campo 'deprecated' del database
        for active_route in active_routes:
            route_name = active_route.path
            route_exists = False

            # Cerca la rotta corrispondente nell'applicazione principale
            for route in app.routes:
                if route.path == route_name:
                    route_exists = True
                    # Imposta il flag deprecated in base al valore del campo 'deprecated' del database
                    deprecate_route([route], route_name, active_route.deprecated, session)

            # Ciclo sui router montati sull'applicazione principale
            for router in app.routers:
                # Cerca la rotta corrispondente nel router
                for route in router.routes:
                    if route.path == route_name:
                        route_exists = True
                        # Imposta il flag deprecated in base al valore del campo 'deprecated' del database
                        deprecate_route([route], route_name, active_route.deprecated, session)

            # Se la rotta non esiste né nell'applicazione principale né nei router montati su di essa, emette un messaggio di warning
            if not route_exists:
                print(f"Warning: Route {route_name} not found in the application or any mounted router.")
    except Exception as e:
        print(f"Error occurred during initialization: {e}")
    finally:
        session.close()

@app.on_event("startup")
async def startup_event():
    # Montaggio dei router sull'applicazione principale
    app.mount("/router1", router1)
    app.mount("/router2", router2)
    app.mount("/router3", router3)

    # Inizializzazione dell'applicazione
    init(app, session)

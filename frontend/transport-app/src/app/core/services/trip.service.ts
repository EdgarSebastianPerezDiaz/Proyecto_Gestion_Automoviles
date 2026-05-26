import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';
import { FulfillmentService } from './fulfillment.service';

export interface Driver {
  id: string;
  name: string;
  license: string;
}

export interface Vehicle {
  id: string;
  plate: string;
  type: string;
}

export type TripStatus = 'Programado' | 'En Ruta' | 'Entregado' | 'Cancelado';
export type LegacyTripStatus = 'Programado' | 'En Ruta' | 'Completado' | 'Cancelado';

export interface TripDocuments {
  ordenCargueUrl?: string;
  manifiestoUrl?: string;
  cumplidoUrl?: string;
}

export interface LegacyTripDocuments {
  waybillNumber: string;
  invoiceNumbers: string[];
  status: string;
}

export interface Trip {
  id: string;
  origenId: string;
  destinoId: string;
  transportistaId: string;
  conductorId: string;
  vehiculoId: string;
  cargoTypeId: string;
  peso: number;
  costoTotal: number;
  fechaSalida: Date;
  fechaLlegadaEstimada: Date;
  fechaLlegadaReal?: Date;
  estado: TripStatus;
  documentos: TripDocuments;
  precioPorTon?: number;
  origenNombre?: string;
  destinoNombre?: string;
  transportistaNombre?: string;
  conductorNombre?: string;
  vehiculoPlaca?: string;
  cargoTypeNombre?: string;
  vehiculoCapacidad?: number;
  origin: string;
  destination: string;
  driver: Driver;
  vehicle: Vehicle;
  status: LegacyTripStatus;
  startDate: Date;
  estimatedEndDate: Date;
  actualEndDate?: Date;
  cargoWeight: number;
  cargoType: string;
  documents: LegacyTripDocuments;
}

export interface PaginatedTrips {
  items: Trip[];
  total: number;
}

interface TripSeed {
  id: string;
  origenId: string;
  destinoId: string;
  transportistaId: string;
  conductorId: string;
  vehiculoId: string;
  cargoTypeId: string;
  peso: number;
  precioPorTon: number;
  fechaSalida: string;
  fechaLlegadaEstimada: string;
  fechaLlegadaReal?: string;
  estado: TripStatus;
  documentos: TripDocuments;
  documents: LegacyTripDocuments;
  origin: string;
  destination: string;
  driver: Driver;
  vehicle: Vehicle;
  cargoType: string;
}

export interface TripReportRow {
  id: string;
  origin: string;
  destination: string;
  conductor: string;
  fechaSalida: Date;
  costoTotal: number;
  estado: TripStatus;
}

const REPORT_TRIPS: Trip[] = [
  {
    id: 'TR-101',
    origenId: 'R1',
    destinoId: 'R11',
    transportistaId: 'T1',
    conductorId: 'D1',
    vehiculoId: 'VH-101',
    cargoTypeId: 'CT-101',
    peso: 26,
    costoTotal: 8320000,
    fechaSalida: new Date('2026-01-08'),
    fechaLlegadaEstimada: new Date('2026-01-09'),
    fechaLlegadaReal: new Date('2026-01-09'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-101.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-101.pdf', cumplidoUrl: 'http://mock/cumplido-TR-101.pdf' },
    precioPorTon: 320000,
    origenNombre: 'Bavaria S.A.',
    destinoNombre: 'Almacenes Éxito S.A.',
    transportistaNombre: 'Jaime Galindo Transportes',
    conductorNombre: 'Jaime Galindo',
    vehiculoPlaca: 'ABC-101',
    cargoTypeNombre: 'Bebidas',
    vehiculoCapacidad: 26,
    origin: 'Bavaria S.A.',
    destination: 'Almacenes Éxito S.A.',
    driver: { id: 'D1', name: 'Jaime Galindo', license: 'LIC-101' },
    vehicle: { id: 'VH-101', plate: 'ABC-101', type: 'Tractomula' },
    status: 'Completado',
    startDate: new Date('2026-01-08'),
    estimatedEndDate: new Date('2026-01-09'),
    actualEndDate: new Date('2026-01-09'),
    cargoWeight: 26,
    cargoType: 'Bebidas',
    documents: { waybillNumber: 'OC-101', invoiceNumbers: ['MV-101'], status: 'pagado' }
  },
  {
    id: 'TR-102',
    origenId: 'R2',
    destinoId: 'R12',
    transportistaId: 'T2',
    conductorId: 'D2',
    vehiculoId: 'VH-102',
    cargoTypeId: 'CT-102',
    peso: 19,
    costoTotal: 6080000,
    fechaSalida: new Date('2026-01-22'),
    fechaLlegadaEstimada: new Date('2026-01-23'),
    fechaLlegadaReal: new Date('2026-01-23'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-102.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-102.pdf', cumplidoUrl: 'http://mock/cumplido-TR-102.pdf' },
    precioPorTon: 320000,
    origenNombre: 'Agropecuaria del Meta',
    destinoNombre: 'Cencosud',
    transportistaNombre: 'Avance MC S.A.S.',
    conductorNombre: 'Carlos Mendoza',
    vehiculoPlaca: 'DEF-102',
    cargoTypeNombre: 'Granos',
    vehiculoCapacidad: 19,
    origin: 'Agropecuaria del Meta',
    destination: 'Cencosud',
    driver: { id: 'D2', name: 'Carlos Mendoza', license: 'LIC-102' },
    vehicle: { id: 'VH-102', plate: 'DEF-102', type: 'Camión' },
    status: 'Completado',
    startDate: new Date('2026-01-22'),
    estimatedEndDate: new Date('2026-01-23'),
    actualEndDate: new Date('2026-01-23'),
    cargoWeight: 19,
    cargoType: 'Granos',
    documents: { waybillNumber: 'OC-102', invoiceNumbers: ['MV-102'], status: 'pendiente' }
  },
  {
    id: 'TR-103',
    origenId: 'R3',
    destinoId: 'R13',
    transportistaId: 'T1',
    conductorId: 'D3',
    vehiculoId: 'VH-103',
    cargoTypeId: 'CT-103',
    peso: 22,
    costoTotal: 7040000,
    fechaSalida: new Date('2026-02-03'),
    fechaLlegadaEstimada: new Date('2026-02-04'),
    fechaLlegadaReal: new Date('2026-02-04'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-103.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-103.pdf', cumplidoUrl: 'http://mock/cumplido-TR-103.pdf' },
    precioPorTon: 320000,
    origenNombre: 'Postobón S.A.',
    destinoNombre: 'Olímpica S.A.',
    transportistaNombre: 'Jaime Galindo Transportes',
    conductorNombre: 'Sebastián Torres',
    vehiculoPlaca: 'GHI-103',
    cargoTypeNombre: 'Bebidas',
    vehiculoCapacidad: 22,
    origin: 'Postobón S.A.',
    destination: 'Olímpica S.A.',
    driver: { id: 'D3', name: 'Sebastián Torres', license: 'LIC-103' },
    vehicle: { id: 'VH-103', plate: 'GHI-103', type: 'Camión' },
    status: 'Completado',
    startDate: new Date('2026-02-03'),
    estimatedEndDate: new Date('2026-02-04'),
    actualEndDate: new Date('2026-02-04'),
    cargoWeight: 22,
    cargoType: 'Bebidas',
    documents: { waybillNumber: 'OC-103', invoiceNumbers: ['MV-103'], status: 'pagado' }
  },
  {
    id: 'TR-104',
    origenId: 'R4',
    destinoId: 'R14',
    transportistaId: 'T2',
    conductorId: 'D4',
    vehiculoId: 'VH-104',
    cargoTypeId: 'CT-104',
    peso: 15,
    costoTotal: 4200000,
    fechaSalida: new Date('2026-02-18'),
    fechaLlegadaEstimada: new Date('2026-02-19'),
    fechaLlegadaReal: new Date('2026-02-19'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-104.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-104.pdf', cumplidoUrl: 'http://mock/cumplido-TR-104.pdf' },
    precioPorTon: 280000,
    origenNombre: 'Nestlé de Colombia',
    destinoNombre: 'Carulla',
    transportistaNombre: 'Avance MC S.A.S.',
    conductorNombre: 'Ana López',
    vehiculoPlaca: 'JKL-104',
    cargoTypeNombre: 'Alimentos',
    vehiculoCapacidad: 15,
    origin: 'Nestlé de Colombia',
    destination: 'Carulla',
    driver: { id: 'D4', name: 'Ana López', license: 'LIC-104' },
    vehicle: { id: 'VH-104', plate: 'JKL-104', type: 'Furgón' },
    status: 'Completado',
    startDate: new Date('2026-02-18'),
    estimatedEndDate: new Date('2026-02-19'),
    actualEndDate: new Date('2026-02-19'),
    cargoWeight: 15,
    cargoType: 'Alimentos',
    documents: { waybillNumber: 'OC-104', invoiceNumbers: ['MV-104'], status: 'pendiente' }
  },
  {
    id: 'TR-105',
    origenId: 'R5',
    destinoId: 'R15',
    transportistaId: 'T1',
    conductorId: 'D5',
    vehiculoId: 'VH-105',
    cargoTypeId: 'CT-105',
    peso: 28,
    costoTotal: 8960000,
    fechaSalida: new Date('2026-03-05'),
    fechaLlegadaEstimada: new Date('2026-03-06'),
    fechaLlegadaReal: new Date('2026-03-06'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-105.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-105.pdf', cumplidoUrl: 'http://mock/cumplido-TR-105.pdf' },
    precioPorTon: 320000,
    origenNombre: 'Cementos Argos',
    destinoNombre: 'Homecenter Sodimac',
    transportistaNombre: 'Jaime Galindo Transportes',
    conductorNombre: 'Luis Pérez',
    vehiculoPlaca: 'MNO-105',
    cargoTypeNombre: 'Materiales',
    vehiculoCapacidad: 28,
    origin: 'Cementos Argos',
    destination: 'Homecenter Sodimac',
    driver: { id: 'D5', name: 'Luis Pérez', license: 'LIC-105' },
    vehicle: { id: 'VH-105', plate: 'MNO-105', type: 'Tractomula' },
    status: 'Completado',
    startDate: new Date('2026-03-05'),
    estimatedEndDate: new Date('2026-03-06'),
    actualEndDate: new Date('2026-03-06'),
    cargoWeight: 28,
    cargoType: 'Materiales',
    documents: { waybillNumber: 'OC-105', invoiceNumbers: ['MV-105'], status: 'pagado' }
  },
  {
    id: 'TR-106',
    origenId: 'R6',
    destinoId: 'R16',
    transportistaId: 'T2',
    conductorId: 'D6',
    vehiculoId: 'VH-106',
    cargoTypeId: 'CT-106',
    peso: 24,
    costoTotal: 7680000,
    fechaSalida: new Date('2026-03-12'),
    fechaLlegadaEstimada: new Date('2026-03-13'),
    fechaLlegadaReal: new Date('2026-03-13'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-106.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-106.pdf', cumplidoUrl: 'http://mock/cumplido-TR-106.pdf' },
    precioPorTon: 320000,
    origenNombre: 'Acerías Paz del Río',
    destinoNombre: 'Éxito S.A.',
    transportistaNombre: 'Avance MC S.A.S.',
    conductorNombre: 'Santiago Ramírez',
    vehiculoPlaca: 'PQR-106',
    cargoTypeNombre: 'Acero',
    vehiculoCapacidad: 24,
    origin: 'Acerías Paz del Río',
    destination: 'Éxito S.A.',
    driver: { id: 'D6', name: 'Santiago Ramírez', license: 'LIC-106' },
    vehicle: { id: 'VH-106', plate: 'PQR-106', type: 'Camión' },
    status: 'Completado',
    startDate: new Date('2026-03-12'),
    estimatedEndDate: new Date('2026-03-13'),
    actualEndDate: new Date('2026-03-13'),
    cargoWeight: 24,
    cargoType: 'Acero',
    documents: { waybillNumber: 'OC-106', invoiceNumbers: ['MV-106'], status: 'pendiente' }
  },
  {
    id: 'TR-107',
    origenId: 'R7',
    destinoId: 'R17',
    transportistaId: 'T1',
    conductorId: 'D7',
    vehiculoId: 'VH-107',
    cargoTypeId: 'CT-107',
    peso: 20,
    costoTotal: 6400000,
    fechaSalida: new Date('2026-03-19'),
    fechaLlegadaEstimada: new Date('2026-03-20'),
    fechaLlegadaReal: new Date('2026-03-20'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-107.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-107.pdf', cumplidoUrl: 'http://mock/cumplido-TR-107.pdf' },
    precioPorTon: 320000,
    origenNombre: 'Bavaria S.A.',
    destinoNombre: 'Surtimax',
    transportistaNombre: 'Jaime Galindo Transportes',
    conductorNombre: 'Carlos Torres',
    vehiculoPlaca: 'STU-107',
    cargoTypeNombre: 'Bebidas',
    vehiculoCapacidad: 20,
    origin: 'Bavaria S.A.',
    destination: 'Surtimax',
    driver: { id: 'D7', name: 'Carlos Torres', license: 'LIC-107' },
    vehicle: { id: 'VH-107', plate: 'STU-107', type: 'Camión' },
    status: 'Completado',
    startDate: new Date('2026-03-19'),
    estimatedEndDate: new Date('2026-03-20'),
    actualEndDate: new Date('2026-03-20'),
    cargoWeight: 20,
    cargoType: 'Bebidas',
    documents: { waybillNumber: 'OC-107', invoiceNumbers: ['MV-107'], status: 'pagado' }
  },
  {
    id: 'TR-108',
    origenId: 'R8',
    destinoId: 'R18',
    transportistaId: 'T2',
    conductorId: 'D8',
    vehiculoId: 'VH-108',
    cargoTypeId: 'CT-108',
    peso: 14,
    costoTotal: 3920000,
    fechaSalida: new Date('2026-01-15'),
    fechaLlegadaEstimada: new Date('2026-01-16'),
    fechaLlegadaReal: new Date('2026-01-16'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-108.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-108.pdf', cumplidoUrl: 'http://mock/cumplido-TR-108.pdf' },
    precioPorTon: 280000,
    origenNombre: 'Tecnoquímicas',
    destinoNombre: 'D1',
    transportistaNombre: 'Avance MC S.A.S.',
    conductorNombre: 'María Suárez',
    vehiculoPlaca: 'VWX-108',
    cargoTypeNombre: 'Químicos',
    vehiculoCapacidad: 14,
    origin: 'Tecnoquímicas',
    destination: 'D1',
    driver: { id: 'D8', name: 'María Suárez', license: 'LIC-108' },
    vehicle: { id: 'VH-108', plate: 'VWX-108', type: 'Furgón' },
    status: 'Completado',
    startDate: new Date('2026-01-15'),
    estimatedEndDate: new Date('2026-01-16'),
    actualEndDate: new Date('2026-01-16'),
    cargoWeight: 14,
    cargoType: 'Químicos',
    documents: { waybillNumber: 'OC-108', invoiceNumbers: ['MV-108'], status: 'pendiente' }
  },
  {
    id: 'TR-109',
    origenId: 'R9',
    destinoId: 'R19',
    transportistaId: 'T1',
    conductorId: 'D9',
    vehiculoId: 'VH-109',
    cargoTypeId: 'CT-109',
    peso: 30,
    costoTotal: 9600000,
    fechaSalida: new Date('2026-02-27'),
    fechaLlegadaEstimada: new Date('2026-02-28'),
    fechaLlegadaReal: new Date('2026-02-28'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-109.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-109.pdf', cumplidoUrl: 'http://mock/cumplido-TR-109.pdf' },
    precioPorTon: 320000,
    origenNombre: 'Mondelez',
    destinoNombre: 'Ara',
    transportistaNombre: 'Jaime Galindo Transportes',
    conductorNombre: 'Luis Gómez',
    vehiculoPlaca: 'YZA-109',
    cargoTypeNombre: 'Snacks',
    vehiculoCapacidad: 30,
    origin: 'Mondelez',
    destination: 'Ara',
    driver: { id: 'D9', name: 'Luis Gómez', license: 'LIC-109' },
    vehicle: { id: 'VH-109', plate: 'YZA-109', type: 'Tractomula' },
    status: 'Completado',
    startDate: new Date('2026-02-27'),
    estimatedEndDate: new Date('2026-02-28'),
    actualEndDate: new Date('2026-02-28'),
    cargoWeight: 30,
    cargoType: 'Snacks',
    documents: { waybillNumber: 'OC-109', invoiceNumbers: ['MV-109'], status: 'pagado' }
  },
  {
    id: 'TR-110',
    origenId: 'R10',
    destinoId: 'R20',
    transportistaId: 'T2',
    conductorId: 'D10',
    vehiculoId: 'VH-110',
    cargoTypeId: 'CT-110',
    peso: 18,
    costoTotal: 5760000,
    fechaSalida: new Date('2026-01-29'),
    fechaLlegadaEstimada: new Date('2026-01-30'),
    fechaLlegadaReal: new Date('2026-01-30'),
    estado: 'Entregado',
    documentos: { ordenCargueUrl: 'http://mock/orden-TR-110.pdf', manifiestoUrl: 'http://mock/manifiesto-TR-110.pdf', cumplidoUrl: 'http://mock/cumplido-TR-110.pdf' },
    precioPorTon: 320000,
    origenNombre: 'Legrand',
    destinoNombre: 'Falabella',
    transportistaNombre: 'Avance MC S.A.S.',
    conductorNombre: 'Santiago Álvarez',
    vehiculoPlaca: 'BCD-110',
    cargoTypeNombre: 'Electrónica',
    vehiculoCapacidad: 18,
    origin: 'Legrand',
    destination: 'Falabella',
    driver: { id: 'D10', name: 'Santiago Álvarez', license: 'LIC-110' },
    vehicle: { id: 'VH-110', plate: 'BCD-110', type: 'Camión' },
    status: 'Completado',
    startDate: new Date('2026-01-29'),
    estimatedEndDate: new Date('2026-01-30'),
    actualEndDate: new Date('2026-01-30'),
    cargoWeight: 18,
    cargoType: 'Electrónica',
    documents: { waybillNumber: 'OC-110', invoiceNumbers: ['MV-110'], status: 'pendiente' }
  }
];

const SEED_TRIPS: TripSeed[] = [
  {
    id: 'TR-001',
    origenId: '1',
    destinoId: 'FR1',
    transportistaId: 'T1',
    conductorId: '1',
    vehiculoId: 'VEH-001',
    cargoTypeId: 'CAR-001',
    peso: 28.5,
    precioPorTon: 320000,
    fechaSalida: '2026-06-15',
    fechaLlegadaEstimada: '2026-06-16',
    estado: 'En Ruta',
    documentos: {
      ordenCargueUrl: 'http://mock/orden-TR-001.pdf',
      manifiestoUrl: 'http://mock/manifiesto-TR-001.pdf'
    },
    documents: {
      waybillNumber: 'OC-001',
      invoiceNumbers: ['MV-001'],
      status: 'pendiente'
    },
    origin: 'Acerías Paz del Río',
    destination: 'Metro de Bogotá S.A.S.',
    driver: { id: '1', name: 'Jaime Galindo', license: 'LIC-001234' },
    vehicle: { id: 'VEH-001', plate: 'XYZ-123', type: 'Tractomula' },
    cargoType: 'Acero estructural'
  },
  {
    id: 'TR-002',
    origenId: '1',
    destinoId: 'FR2',
    transportistaId: 'T1',
    conductorId: '2',
    vehiculoId: 'VEH-002',
    cargoTypeId: 'CAR-002',
    peso: 22,
    precioPorTon: 180000,
    fechaSalida: '2026-06-18',
    fechaLlegadaEstimada: '2026-06-19',
    estado: 'Programado',
    documentos: {
      ordenCargueUrl: 'http://mock/orden-TR-002.pdf'
    },
    documents: {
      waybillNumber: 'OC-002',
      invoiceNumbers: [],
      status: 'pendiente'
    },
    origin: 'Acerías Paz del Río',
    destination: 'Homecenter Sodimac',
    driver: { id: '2', name: 'Sebastián Torres', license: 'LIC-005678' },
    vehicle: { id: 'VEH-002', plate: 'ABC-456', type: 'Camión' },
    cargoType: 'Chatarra metálica'
  },
  {
    id: 'TR-003',
    origenId: '2',
    destinoId: 'FR3',
    transportistaId: 'T2',
    conductorId: '3',
    vehiculoId: 'VEH-003',
    cargoTypeId: 'CAR-003',
    peso: 25,
    precioPorTon: 290000,
    fechaSalida: '2026-06-10',
    fechaLlegadaEstimada: '2026-06-11',
    fechaLlegadaReal: '2026-06-11',
    estado: 'Entregado',
    documentos: {
      ordenCargueUrl: 'http://mock/orden-TR-003.pdf',
      manifiestoUrl: 'http://mock/manifiesto-TR-003.pdf',
      cumplidoUrl: 'http://mock/cumplido-TR-003.pdf'
    },
    documents: {
      waybillNumber: 'OC-003',
      invoiceNumbers: ['MV-003'],
      status: 'pagado'
    },
    origin: 'TransCarga S.A.',
    destination: 'Almacenes Éxito S.A.',
    driver: { id: '3', name: 'Carlos Mendoza', license: 'LIC-009900' },
    vehicle: { id: 'VEH-003', plate: 'DEF-789', type: 'Camión' },
    cargoType: 'Tubería industrial'
  }
];

@Injectable({
  providedIn: 'root'
})
export class TripService {
  private trips: Trip[] = [];
  private nextId = 4;

  constructor(private fulfillmentService: FulfillmentService) {
    this.trips = SEED_TRIPS.map(trip => this.cloneTrip(this.seedToTrip(trip)));
  }

  private seedToTrip(seed: TripSeed): Trip {
    return {
      id: seed.id,
      origenId: seed.origenId,
      destinoId: seed.destinoId,
      transportistaId: seed.transportistaId,
      conductorId: seed.conductorId,
      vehiculoId: seed.vehiculoId,
      cargoTypeId: seed.cargoTypeId,
      peso: seed.peso,
      costoTotal: seed.peso * seed.precioPorTon,
      fechaSalida: new Date(seed.fechaSalida),
      fechaLlegadaEstimada: new Date(seed.fechaLlegadaEstimada),
      fechaLlegadaReal: seed.fechaLlegadaReal ? new Date(seed.fechaLlegadaReal) : undefined,
      estado: seed.estado,
      documentos: { ...seed.documentos },
      precioPorTon: seed.precioPorTon,
      origenNombre: seed.origin,
      destinoNombre: seed.destination,
      transportistaNombre: seed.transportistaId === 'T1' ? 'Jaime Galindo Transportes' : 'Avance MC S.A.S.',
      conductorNombre: seed.driver.name,
      vehiculoPlaca: seed.vehicle.plate,
      cargoTypeNombre: seed.cargoType,
      vehiculoCapacidad: seed.peso,
      origin: seed.origin,
      destination: seed.destination,
      driver: { ...seed.driver },
      vehicle: { ...seed.vehicle },
      status: seed.estado === 'Entregado' ? 'Completado' : seed.estado,
      startDate: new Date(seed.fechaSalida),
      estimatedEndDate: new Date(seed.fechaLlegadaEstimada),
      actualEndDate: seed.fechaLlegadaReal ? new Date(seed.fechaLlegadaReal) : undefined,
      cargoWeight: seed.peso,
      cargoType: seed.cargoType,
      documents: { ...seed.documents }
    };
  }

  private cloneTrip(trip: Trip): Trip {
    return {
      ...trip,
      fechaSalida: new Date(trip.fechaSalida),
      fechaLlegadaEstimada: new Date(trip.fechaLlegadaEstimada),
      fechaLlegadaReal: trip.fechaLlegadaReal ? new Date(trip.fechaLlegadaReal) : undefined,
      documentos: { ...trip.documentos },
      driver: { ...trip.driver },
      vehicle: { ...trip.vehicle },
      startDate: new Date(trip.startDate),
      estimatedEndDate: new Date(trip.estimatedEndDate),
      actualEndDate: trip.actualEndDate ? new Date(trip.actualEndDate) : undefined,
      documents: {
        waybillNumber: trip.documents.waybillNumber,
        invoiceNumbers: [...trip.documents.invoiceNumbers],
        status: trip.documents.status
      }
    };
  }

  private nextTripId(): string {
    const id = `TR-${String(this.nextId).padStart(3, '0')}`;
    this.nextId++;
    return id;
  }

  private buildDocuments(tripId: string, state: TripStatus, existing?: TripDocuments): TripDocuments {
    const documents: TripDocuments = { ...existing };

    if (!documents.ordenCargueUrl) {
      documents.ordenCargueUrl = `http://mock/orden-${tripId}.pdf`;
    }

    if (!documents.manifiestoUrl) {
      documents.manifiestoUrl = `http://mock/manifiesto-${tripId}.pdf`;
    }

    if (state === 'Entregado' && !documents.cumplidoUrl) {
      documents.cumplidoUrl = `http://mock/cumplido-${tripId}.pdf`;
    }

    return documents;
  }

  private buildLegacyDocuments(tripId: string, existing?: LegacyTripDocuments): LegacyTripDocuments {
    return {
      waybillNumber: existing?.waybillNumber || `OC-${tripId.replace('TR-', '')}`,
      invoiceNumbers: existing?.invoiceNumbers?.length ? [...existing.invoiceNumbers] : [`MV-${tripId.replace('TR-', '')}`],
      status: existing?.status || 'generado'
    };
  }

  private normalizeStatus(status: TripStatus): LegacyTripStatus {
    return status === 'Entregado' ? 'Completado' : status;
  }

  private hydrateTrip(trip: Trip): Trip {
    return this.cloneTrip({
      ...trip,
      status: this.normalizeStatus(trip.estado),
      startDate: new Date(trip.fechaSalida),
      estimatedEndDate: new Date(trip.fechaLlegadaEstimada),
      actualEndDate: trip.fechaLlegadaReal ? new Date(trip.fechaLlegadaReal) : undefined,
      origin: trip.origin || trip.origenNombre || '',
      destination: trip.destination || trip.destinoNombre || '',
      driver: trip.driver ? { ...trip.driver } : { id: trip.conductorId, name: trip.conductorNombre || '', license: '' },
      vehicle: trip.vehicle ? { ...trip.vehicle } : { id: trip.vehiculoId, plate: trip.vehiculoPlaca || '', type: '' },
      cargoWeight: trip.peso,
      cargoType: trip.cargoType || trip.cargoTypeNombre || '',
      documents: trip.documents ? { ...trip.documents } : { waybillNumber: '', invoiceNumbers: [], status: 'pendiente' }
    });
  }

  getTrips(page: number = 1, limit: number = 10, search: string = '', statusFilter: TripStatus | 'todos' = 'todos'): Observable<PaginatedTrips> {
    return of(null).pipe(
      delay(300),
      map(() => {
        let filtered = [...this.trips];

        if (statusFilter !== 'todos') {
          filtered = filtered.filter(trip => trip.estado === statusFilter);
        }

        if (search.trim()) {
          const searchTerm = search.toLowerCase().trim();
          filtered = filtered.filter(trip =>
            trip.id.toLowerCase().includes(searchTerm) ||
            (trip.origenNombre || trip.origin).toLowerCase().includes(searchTerm) ||
            (trip.destinoNombre || trip.destination).toLowerCase().includes(searchTerm)
          );
        }

        const total = filtered.length;
        const start = (page - 1) * limit;
        const items = filtered.slice(start, start + limit).map(trip => this.hydrateTrip(trip));

        return { items, total };
      })
    );
  }

  getActiveTrips(): Observable<Trip[]> {
    return this.getTrips(1, this.trips.length || 1, '', 'todos').pipe(
      map(result => result.items)
    );
  }

  getTripsForReport(from: Date, to: Date): Observable<TripReportRow[]> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const fromTime = new Date(from).setHours(0, 0, 0, 0);
        const toTime = new Date(to).setHours(23, 59, 59, 999);
        return [...this.trips, ...REPORT_TRIPS]
          .filter(trip => {
            const time = new Date(trip.fechaSalida).getTime();
            return time >= fromTime && time <= toTime;
          })
          .sort((a, b) => a.fechaSalida.getTime() - b.fechaSalida.getTime())
          .map(trip => ({
            id: trip.id,
            origin: trip.origin || trip.origenNombre || '',
            destination: trip.destination || trip.destinoNombre || '',
            conductor: trip.conductorNombre || trip.driver?.name || '',
            fechaSalida: new Date(trip.fechaSalida),
            costoTotal: trip.costoTotal,
            estado: trip.estado
          }));
      })
    );
  }

  getDeliveredTripsWithoutFulfillment(): Observable<Trip[]> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const tripIdsWithFulfillment = this.fulfillmentService.getFulfillmentTripIds();
        return this.trips
          .filter(trip => trip.estado === 'Entregado' && !tripIdsWithFulfillment.includes(trip.id))
          .map(trip => this.hydrateTrip(trip));
      })
    );
  }

  getTripById(tripId: string): Observable<Trip | undefined> {
    return of(this.trips.find(trip => trip.id === tripId)).pipe(
      delay(300),
      map(trip => trip ? this.hydrateTrip(trip) : undefined)
    );
  }

  createTrip(trip: Partial<Trip> & { precioPorTon?: number }): Observable<Trip> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const id = this.nextTripId();
        const created: Trip = {
          id,
          origenId: trip.origenId || '',
          destinoId: trip.destinoId || '',
          transportistaId: trip.transportistaId || '',
          conductorId: trip.conductorId || '',
          vehiculoId: trip.vehiculoId || '',
          cargoTypeId: trip.cargoTypeId || '',
          peso: Number(trip.peso || 0),
          costoTotal: Number(trip.peso || 0) * Number(trip.precioPorTon || 0),
          fechaSalida: trip.fechaSalida ? new Date(trip.fechaSalida) : new Date(),
          fechaLlegadaEstimada: trip.fechaLlegadaEstimada ? new Date(trip.fechaLlegadaEstimada) : new Date(),
          fechaLlegadaReal: undefined,
          estado: 'Programado',
          documentos: this.buildDocuments(id, 'Programado', trip.documentos),
          precioPorTon: trip.precioPorTon,
          origenNombre: trip.origenNombre || trip.origin || '',
          destinoNombre: trip.destinoNombre || trip.destination || '',
          transportistaNombre: trip.transportistaNombre,
          conductorNombre: trip.conductorNombre,
          vehiculoPlaca: trip.vehiculoPlaca,
          cargoTypeNombre: trip.cargoTypeNombre || trip.cargoType || '',
          vehiculoCapacidad: trip.vehiculoCapacidad,
          origin: trip.origin || trip.origenNombre || '',
          destination: trip.destination || trip.destinoNombre || '',
          driver: trip.driver ? { ...trip.driver } : { id: trip.conductorId || '', name: trip.conductorNombre || '', license: '' },
          vehicle: trip.vehicle ? { ...trip.vehicle } : { id: trip.vehiculoId || '', plate: trip.vehiculoPlaca || '', type: '' },
          status: 'Programado',
          startDate: trip.fechaSalida ? new Date(trip.fechaSalida) : new Date(),
          estimatedEndDate: trip.fechaLlegadaEstimada ? new Date(trip.fechaLlegadaEstimada) : new Date(),
          actualEndDate: undefined,
          cargoWeight: Number(trip.peso || 0),
          cargoType: trip.cargoType || trip.cargoTypeNombre || '',
          documents: this.buildLegacyDocuments(id, trip.documents as LegacyTripDocuments | undefined)
        };

        this.trips.push(created);
        return this.hydrateTrip(created);
      })
    );
  }

  updateTrip(id: string, updates: Partial<Trip>): Observable<Trip> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.trips.findIndex(trip => trip.id === id);
        if (index === -1) {
          throw new Error(`Trip with id ${id} not found`);
        }

        const current = this.trips[index];
        const merged: Trip = {
          ...current,
          ...updates,
          id,
          fechaSalida: updates.fechaSalida ? new Date(updates.fechaSalida) : current.fechaSalida,
          fechaLlegadaEstimada: updates.fechaLlegadaEstimada ? new Date(updates.fechaLlegadaEstimada) : current.fechaLlegadaEstimada,
          fechaLlegadaReal: updates.fechaLlegadaReal ? new Date(updates.fechaLlegadaReal) : current.fechaLlegadaReal,
          peso: updates.peso !== undefined ? Number(updates.peso) : current.peso,
          costoTotal: updates.costoTotal !== undefined ? Number(updates.costoTotal) : current.costoTotal,
          origenNombre: updates.origenNombre ?? current.origenNombre,
          destinoNombre: updates.destinoNombre ?? current.destinoNombre,
          transportistaNombre: updates.transportistaNombre ?? current.transportistaNombre,
          conductorNombre: updates.conductorNombre ?? current.conductorNombre,
          vehiculoPlaca: updates.vehiculoPlaca ?? current.vehiculoPlaca,
          cargoTypeNombre: updates.cargoTypeNombre ?? current.cargoTypeNombre,
          vehiculoCapacidad: updates.vehiculoCapacidad ?? current.vehiculoCapacidad,
          documentos: updates.documentos ? { ...updates.documentos } : current.documentos,
          status: updates.status ?? current.status,
          origin: updates.origin ?? current.origin,
          destination: updates.destination ?? current.destination,
          driver: updates.driver ? { ...updates.driver } : current.driver,
          vehicle: updates.vehicle ? { ...updates.vehicle } : current.vehicle,
          startDate: updates.startDate ? new Date(updates.startDate) : current.startDate,
          estimatedEndDate: updates.estimatedEndDate ? new Date(updates.estimatedEndDate) : current.estimatedEndDate,
          actualEndDate: updates.actualEndDate ? new Date(updates.actualEndDate) : current.actualEndDate,
          cargoWeight: updates.cargoWeight !== undefined ? Number(updates.cargoWeight) : current.cargoWeight,
          cargoType: updates.cargoType ?? current.cargoType,
          documents: updates.documents ? { ...updates.documents as LegacyTripDocuments } : current.documents
        };

        merged.status = this.normalizeStatus(merged.estado);
        merged.startDate = new Date(merged.fechaSalida);
        merged.estimatedEndDate = new Date(merged.fechaLlegadaEstimada);
        merged.actualEndDate = merged.fechaLlegadaReal ? new Date(merged.fechaLlegadaReal) : undefined;
        merged.documents = this.buildLegacyDocuments(id, merged.documents);

        this.trips[index] = merged;
        return this.hydrateTrip(merged);
      })
    );
  }

  updateTripStatus(tripId: string, newStatus: TripStatus | LegacyTripStatus): Observable<Trip> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.trips.findIndex(trip => trip.id === tripId);
        if (index === -1) {
          throw new Error(`Trip ${tripId} not found`);
        }

        const current = this.trips[index];
        const normalizedStatus: TripStatus = newStatus === 'Completado' ? 'Entregado' : newStatus;
        const allowed = this.getAllowedStatusTransitions(current.estado);
        if (!allowed.includes(normalizedStatus)) {
          throw new Error(`Transition from ${current.estado} to ${normalizedStatus} is not allowed`);
        }

        const updated: Trip = {
          ...current,
          estado: normalizedStatus,
          status: this.normalizeStatus(normalizedStatus),
          fechaLlegadaReal: normalizedStatus === 'Entregado' ? new Date() : current.fechaLlegadaReal,
          actualEndDate: normalizedStatus === 'Entregado' ? new Date() : current.actualEndDate,
          documentos: this.buildDocuments(current.id, normalizedStatus, current.documentos),
          documents: {
            ...current.documents,
            status: normalizedStatus === 'Entregado' ? 'pagado' : current.documents.status
          }
        };

        this.trips[index] = updated;

        if (normalizedStatus === 'Entregado' && !this.fulfillmentService.hasFulfillmentForTrip(current.id)) {
          this.fulfillmentService.createFulfillment({
            tripId: current.id,
            tripNombre: `${updated.origenNombre || updated.origin} → ${updated.destinoNombre || updated.destination}`,
            fechaEntrega: new Date(),
            horaEntrega: new Date().toTimeString().slice(0, 5),
            recibidoPor: 'Por definir',
            observaciones: 'Generado automáticamente al marcar el viaje como entregado',
            estadoPago: 'Pendiente'
          }).subscribe({
            error: error => console.error('Error creando cumplido automático:', error)
          });
        }

        return this.hydrateTrip(updated);
      })
    );
  }

  reconcileDocuments(tripId: string): Observable<Trip> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.trips.findIndex(trip => trip.id === tripId);
        if (index === -1) {
          throw new Error(`Trip ${tripId} not found`);
        }

        const current = this.trips[index];
        const updated: Trip = {
          ...current,
          documentos: this.buildDocuments(current.id, current.estado, current.documentos),
          documents: this.buildLegacyDocuments(current.id, current.documents)
        };

        this.trips[index] = updated;
        return this.hydrateTrip(updated);
      })
    );
  }

  private getAllowedStatusTransitions(currentStatus: TripStatus): TripStatus[] {
    switch (currentStatus) {
      case 'Programado':
        return ['En Ruta', 'Cancelado'];
      case 'En Ruta':
        return ['Entregado', 'Cancelado'];
      case 'Entregado':
      case 'Cancelado':
      default:
        return [];
    }
  }
}

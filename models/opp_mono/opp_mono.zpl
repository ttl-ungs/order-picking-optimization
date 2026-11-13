##############################################################################
# OPP-Mono (modelo monolitico) - ZIMPL Formulation
# Modelo con asignación de lotes a pickers.
#
# Resuelve EL MISMO problema que opp_split (la descomposicion en dos
# etapas: opp_split_stage1_routing.zpl + opp_split_stage2_scheduling.zpl), pero como un unico MIP
# monolitico: ruteo + asignacion + secuenciacion se deciden juntos. Incluye las
# dos extensiones del problema:
#   - Pickers heterogeneos por velocidad (V_p): la velocidad escala solo el
#     tiempo de traslado+servicio de la ruta (r_b), NO el setup ni el
#     picking (T_setup, T_pick): duracion del lote = F_b[b] + r_b[b]/V_p[p]
#   - Cadena de frio: un lote solo puede asignarse a un picker si, a la
#     velocidad de ESE picker, F_b[b] + r_b[b]/V_p[p] <= T_cold (+EPS, misma
#     tolerancia que opp_split/opp_hc/opp_aco).
# y toma de opp_split dos mejoras de formulacion que no cambian el problema:
# objetivo sobre c_b (no sobre c_pb de todos los pares) y filas de
# tardanza/adelanto solo para pares (n,b) con B_nb = 1.
# Con V_p = 1 para todos los pickers y T_cold muy grande (defaults que
# escribe dat_files_builder cuando el escenario no los define) el modelo se
# reduce al problema sin velocidades ni cadena de frio.
#
# Supuestos LP (del PDF "Supuestos de la Programacion Lineal"):
#   Proporcionalidad : cada termino de la FO y restricciones es lineal en sus vars.
#   Aditividad       : FO y restricciones son combinaciones lineales (sin productos
#                      entre variables de decision).
#   Divisibilidad    : variables continuas (ta_n, ea_n, r_b, u_pb, c_pb, c_b, q_ijb)
#                      pueden tomar cualquier valor real >= 0.
#   Certeza          : todos los parametros (distancias, capacidades, pesos,
#                      fechas) son conocidos y fijos.
##############################################################################


##############################################################################
# SETS
##############################################################################

# N : ordenes de clientes
set N := { read "../dat_files/data_N.dat" as "<1s>" comment "#" };

# V : locaciones totales del almacen (incluye v_start y v_end)
set V := { read "../dat_files/data_V.dat" as "<1s>" comment "#" };

# P : pickers
set P := { read "../dat_files/data_P.dat" as "<1s>" comment "#" };

# B : lotes de pedidos factibles
set B := { read "../dat_files/data_B.dat" as "<1s>" comment "#" };

# E : arcos validos del grafo de locaciones
set E := { read "../dat_files/data_E.dat" as "<1s,2s>" comment "#" };


##############################################################################
# PARAMETERS
##############################################################################

# Nodos especiales (leidos de .dat para que el modelo sea independiente del escenario)
param v_start := read "../dat_files/depot.dat" as "1s" comment "#";   # deposito inicial
param v_end   := read "../dat_files/final.dat" as "1s" comment "#";   # nodo final

# Pesos de la funcion objetivo
param W_c   := read "../dat_files/params.dat" as "1n" skip 0 comment "#";  # peso tiempo de completitud
param W_pen := read "../dat_files/params.dat" as "1n" skip 1 comment "#";  # peso penalizaciones (adelanto + tardanza)
param W_e   := read "../dat_files/params.dat" as "1n" skip 2 comment "#";  # peso adelanto
param W_t   := read "../dat_files/params.dat" as "1n" skip 3 comment "#";  # peso tardanza

# Parametros de tiempo
param T_travel := read "../dat_files/params.dat" as "1n" skip 4 comment "#";  # tiempo por unidad de distancia
param T_setup  := read "../dat_files/params.dat" as "1n" skip 5 comment "#";  # tiempo de setup por lote
param T_pick   := read "../dat_files/params.dat" as "1n" skip 6 comment "#";  # tiempo de picking por unidad de capacidad

# Capacidades --> NO USADO EN ESTE MODELO.
# param C_v       := read "../dat_files/params.dat" as "1n" skip 7 comment "#";  # capacidad del vehiculo de picking

# Big-M
param M         := read "../dat_files/params.dat" as "1n" skip 8 comment "#";  # entero suficientemente grande

# V_p[p] : factor de velocidad del picker p (1.0 = referencia; >1 = mas rapido)
param V_p[P]    := read "../dat_files/velocities.dat" as "<1s> 2n" comment "#";

# T_cold : tiempo maximo (mismas unidades que la duracion del lote) que un
#          lote puede estar fuera de la camara de frio durante el armado
param T_cold := read "../dat_files/cold.dat" as "1n" comment "#";

# EPS : tolerancia de punto flotante del chequeo de cadena de frio (la misma
#       que usan opp_split, opp_hc y opp_aco)
param EPS := 1e-9;

# C_n[n] : capacidad requerida para la orden n
param C_n[N]    := read "../dat_files/cap_n.dat"      as "<1s> 2n" comment "#";

# T_due_n[n] : fecha limite (due date) de la orden n
param T_due_n[N] := read "../dat_files/due_date.dat"   as "<1s> 2n" comment "#";

# D_ij[(i,j)] : distancia entre locaciones i y j  (solo arcos validos)
param D_ij[E]    := read "../dat_files/distances.dat"  as "<1s,2s> 3n" comment "#";

# S_i[i] : tiempo de servicio en la locacion i
param S_i[V]    := read "../dat_files/service_time.dat" as "<1s> 2n" comment "#";

# A_ni[n,i] : 1 si la orden n debe visitar la locacion i, 0 si no
param A_ni[N * V] := read "../dat_files/a_ni.dat"    as "<1s,2s> 3n" comment "#";

# B_nb[n,b] : 1 si el lote b contiene la orden n, 0 si no
param B_nb[N * B] := read "../dat_files/B_nb.dat"      as "<1s,2s> 3n" comment "#";

# L_b[b] : numero de locaciones distintas requeridas por el lote b
#          (parametro derivado; L_b = |{i in V\{v_start,v_end} : sum_n A_ni[n,i]*B_nb[n,b] >= 1}|)
param L_b[<b> in B] :=
    sum <i> in V with (i != v_start and i != v_end and (sum <n> in N : A_ni[n,i] * B_nb[n,b]) >= 1) : 1;

# F_b[b] : parte de la duracion del lote que NO depende de la ruta
#          (setup + picking en si), por lo tanto tampoco del picker
param F_b[<b> in B] :=
    T_setup + T_pick * (sum <n> in N: C_n[n] * B_nb[n,b]);

param M_seq := read "../dat_files/params.dat" as "1n" skip 9 comment "#";

##############################################################################
# VARIABLES
##############################################################################

# ta_n[n] : tardanza de la orden n  (continua >= 0)
var ta_n[N]         >= 0;

# ea_n[n] : adelanto de la orden n  (continua >= 0)
var ea_n[N]         >= 0;

# r_b[b] : tiempo de traslado + servicio de la ruta elegida para el lote b
#          (continua >= 0). Es el mismo concepto que exporta la Etapa 1 de
#          opp_split; aca NO es dato sino que se decide junto con la ruta.
var r_b[B]          >= 0;

# c_b[b] : tiempo de completitud del lote b  (continua >= 0)
#          [nueva variable de la especificacion; representa el makespan agregado
#           del lote, independiente del picker]
var c_b[B]          >= 0;

# u_pb[p,b] : tiempo de procesamiento del lote b asignado al picker p
#
# La cota superior implementa la cadena de frio: si x_pb = 1, (15) obliga a
# u_pb >= F_b[b] + r_b[b]/V_p[p], asi que esa duracion queda <= T_cold + EPS
# (la misma condicion que PB_elig de opp_split_stage2_scheduling.zpl);
# si x_pb = 0 la cota no restringe nada porque u_pb puede valer 0.
var u_pb[P * B]     >= 0 <= T_cold + EPS;

# c_pb[p,b] : tiempo de completitud del lote b del picker p
#
var c_pb[P * B]     >= 0;

# z_ijb[i,j,b] : 1 si el arco (i,j) esta incluido en el lote b  (binaria)
#var z_ijb[V * V * B]  binary;

# z_ijb[i,j,b] : 1 si el arco valido (i,j) esta incluido en el lote b --> redefinimos la variable para que considere solo arcos válidos
var z_ijb[E * B] binary;

# q_ijb[i,j,b] : flujo de carga de Gavish-Graves: cantidad de locaciones
#                requeridas del lote b que todavia faltan visitar al recorrer
#                el arco valido (i,j) (continua >= 0). Solo existe para
#                eliminar subtours.
#var q_ijb[V * V * B]  >= 0;
var q_ijb[E * B] >= 0;

##############################################################################
# VARIABLES DE ASIGNACION Y VELOCIDAD
##############################################################################

# x_pb[p,b] : 1 si el lote b es asignado al picker p
var x_pb[P * B] binary;

# y_bk[b,k] : 1 si, en el picker que comparten, el lote b va antes que el k
#             (solo definida para pares b < k)
var y_bk[<b,k> in B * B with b < k] binary;

##############################################################################
# OBJECTIVE FUNCTION
#
# min  W_c * sum_b c_b[b]
#    + W_pen * ( W_e * sum_n ea_n[n]  +  W_t * sum_n ta_n[n] )
#
# Nota: c_b se vincula a c_pb mediante las restricciones de completitud (ver
# abajo). Igual que en opp_split, el objetivo suma la completitud de cada lote en
# el picker que lo ejecuta (no c_pb sobre todos los pares (p,b), donde un
# c_pb > 0 forzado en un par NO asignado se pagaria sin corresponder a ningun
# lote real).
##############################################################################

minimize obj:
      W_c  * (sum <b> in B: c_b[b])
    + W_pen * (  W_e * (sum <n> in N: ea_n[n])
                 + W_t * (sum <n> in N: ta_n[n])
                );


##############################################################################
# CONSTRAINTS
##############################################################################

############################### Rutas de lote ################################

# (1) Cada lote sale una vez del depósito
subto start_from_depot:
  forall <b> in B:
      sum <i, j> in E with i == v_start:
          z_ijb[i, j, b] == 1;

# (2) Cada lote entra una vez al nodo final
subto finish_at_end:
   forall <b> in B:
       sum <i, j> in E with j == v_end:
           z_ijb[i, j, b] == 1;

# (3) No hay retorno al depósito inicial - Nueva constraint
subto no_inflow_depot:
    forall <b> in B:
        sum <i, j> in E with j == v_start and v_start != v_end:
            z_ijb[i, j, b] == 0;

# (4) No hay salida desde el nodo final - Nueva constraint
subto no_outflow_final:
    forall <b> in B:
        sum <i, j> in E with i == v_end and v_start != v_end:
            z_ijb[i, j, b] == 0;

####################### Visita y conservación de flujo #######################

# (5) Entrada a locaciones requeridas
subto force_visit_inflow:
   forall <b> in B:
       forall <j> in V with j != v_start and j != v_end:
           sum <i, j> in E:
               z_ijb[i, j, b]
           >= if (sum <n> in N: A_ni[n,j] * B_nb[n,b]) >= 1 then 1 else 0 end;

# (6) Salida de locaciones requeridas
subto force_visit_outflow:
    forall <b> in B:
        forall <j> in V with j != v_start and j != v_end:
            sum <j, i> in E:
                z_ijb[j, i, b]
            >= if (sum <n> in N: A_ni[n,j] * B_nb[n,b]) >= 1 then 1 else 0 end;

# (7) Conservación en nodos intermedios
subto route_flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_start and i != v_end:
            (sum <g, i> in E: z_ijb[g, i, b])
            - (sum <i, j> in E: z_ijb[i, j, b]) == 0;

# (8) A lo sumo un arco de entrada por nodo
subto one_input_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_start:
            sum <j, i> in E:
                z_ijb[j, i, b] <= 1;

# (9) A lo sumo un arco de salida por nodo
subto one_output_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_end:
            sum <i, j> in E:
                z_ijb[i, j, b] <= 1;

#################### Subtour elimination y flujo de carga ####################

# (10) El flujo de carga solo circula por arcos usados (Gavish-Graves)
subto load_flow_bound:
    forall <b> in B:
        forall <i, j> in E:
            q_ijb[i, j, b] - L_b[b] * z_ijb[i, j, b] <= 0;

# (11) Flujo total desde el depósito
subto load_flow_source:
    forall <b> in B:
        sum <i, j> in E with i == v_start:
            q_ijb[i, j, b] == L_b[b];

# (12) Balance Gavish-Graves
subto load_flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_start and i != v_end:
            (sum <g, i> in E: q_ijb[g, i, b])
            - (sum <i, j> in E: q_ijb[i, j, b])
            == if (sum <n> in N: A_ni[n,i] * B_nb[n,b]) >= 1 then 1 else 0 end;

##################### Tiempo de ejecución y completitud ######################

# (13) Tiempo de ruta del lote (traslado + servicio)
# r_b[b] = traslado (distancia * T_travel) + servicio en cada ubicacion
# visitada. NO incluye T_setup ni T_pick (ver F_b): esos no dependen
# de la ruta. Es la misma definicion que define_route_time de
# opp_split_stage1_routing.zpl (opp_split); la unica diferencia es que aca la ruta y su
# tiempo se deciden en el mismo MIP que la asignacion y la secuenciacion.
subto define_route_time:
    forall <b> in B:
        r_b[b] ==
              T_travel * (sum <i,j> in E with i != v_end and j != v_start:
                               D_ij[i,j] * z_ijb[i,j,b])
            + (sum <i> in V with i != v_start and i != v_end:
                   S_i[i] * (sum <i, j> in E: z_ijb[i, j, b]));

#################### Asignación de lotes y secuenciación #####################

# (14) Asignación única por lote a un picker - Nueva constraint
subto assign_exactly_one_picker:
    forall <b> in B:
        sum <p> in P: x_pb[p,b] == 1;

# (15) Ejecución acota procesamiento (cota inferior)
# duracion = F_b[b] + r_b[b] / V_p[p]  (solo la ruta escala con la
# velocidad del picker, igual que T_exec_pb de opp_split_stage2_scheduling.zpl).
#   F_b[b] + r_b[b]/V_p[p] - M * (1 - x_pb[p,b]) <= u_pb[p,b]
subto batch_execution_time_lower:
    forall <p,b> in P * B:
        F_b[b] + r_b[b] / V_p[p] - M * (1 - x_pb[p,b]) <= u_pb[p,b];

# (16) cota superior; fija u_pb = F_b[b] + r_b[b]/V_p[p] cuando x_pb=1
subto batch_execution_time_upper:
    forall <p,b> in P * B:
        u_pb[p,b] <= F_b[b] + r_b[b] / V_p[p] + M * (1 - x_pb[p,b]);

# (17) Procesamiento precede a completitud
subto processing_le_completion:
    forall <p,b> in P * B:
        u_pb[p,b] <= c_pb[p,b];

# (18) Completitud del lote vs picker
# c_b[b] se define como el maximo de c_pb[p,b] sobre los pickers que tienen
# asignado el lote b.  Se linealiza como:
#   c_pb[p,b] - M * (1 - x_pb[p,b]) <= c_b[b]   forall p, b
subto c_b_lower_bound:
    forall <p,b> in P * B:
        c_pb[p,b] - M * (1 - x_pb[p,b]) <= c_b[b];

###################### Secuenciamiento sin solapamiento ######################

# (19) Secuenciamiento sin solapamiento (orden 1) - Nueva constraint
# Si ambos lotes se asignan al mismo picker, uno debe ejecutarse después del otro.
# La duracion del lote k depende del picker p (velocidad V_p[p]), igual que
# T_exec_pb[p,k] en opp_split_stage2_scheduling.zpl.
subto non_overlap_1:
    forall <p> in P:
        forall <b, k> in B * B with b < k:
            c_pb[p,k] >= c_pb[p,b] + F_b[k] + r_b[k] / V_p[p]
                         - M_seq * (3 - x_pb[p,b] - x_pb[p,k] - y_bk[b,k]);

# (20) Secuenciamiento sin solapamiento (orden 2) - Nueva constraint
subto non_overlap_2:
    forall <p> in P:
        forall <b, k> in B * B with b < k:
            c_pb[p,b] >= c_pb[p,k] + F_b[b] + r_b[b] / V_p[p]
                         - M_seq * (2 - x_pb[p,b] - x_pb[p,k] + y_bk[b,k]);

########################### Earliness y tardiness ############################

# Filtradas por B_nb[n,b] == 1 (igual que opp_split_stage2_scheduling.zpl): para un par
# (n,b) con B_nb = 0 la restriccion nunca es activa (M es cota valida), asi que
# generarla solo agrega filas.

# (21) Definición de tardanza
# c_pb[p,b] - T_due_n[n] - M * (2 - x_pb[p,b] - B_nb[n,b]) <= ta_n[n]
subto tardiness_definition:
    forall <p,b,n> in P * B * N with B_nb[n,b] == 1:
        c_pb[p,b] - T_due_n[n] - M * (2 - x_pb[p,b] - B_nb[n,b]) <= ta_n[n];

# (22) Definición de adelanto
# T_due_n[n] - c_pb[p,b] - M * (2 - x_pb[p,b] - B_nb[n,b]) <= ea_n[n]
subto earliness_definition:
    forall <p,b,n> in P * B * N with B_nb[n,b] == 1:
        T_due_n[n] - c_pb[p,b] - M * (2 - x_pb[p,b] - B_nb[n,b]) <= ea_n[n];

##############################################################################
# OPP Model V5.1 (monolitico) - ZIMPL Formulation
# Basado en: opp_v4 (opp_model_v4.zpl) y models.pdf (Segunda Version).
# Modelo con asignación de lotes a pickers.
#
# Resuelve EL MISMO problema que opp_v5_2_split (la descomposicion en dos
# etapas: stage1_routing.zpl + stage2_scheduling.zpl), pero como un unico MIP
# monolitico: ruteo + asignacion + secuenciacion se deciden juntos. Respecto de
# opp_v4 agrega las dos extensiones de la familia v5:
#   - Pickers heterogeneos por velocidad (V_p): la velocidad escala solo el
#     tiempo de traslado+servicio de la ruta (R_b_time), NO el setup ni el
#     picking (B_setup, B_picking).  t_exec_pb = tiempo_fijo[b] + R_b_time[b]/V_p[p]
#   - Cadena de frio: un lote solo puede asignarse a un picker si, a la
#     velocidad de ESE picker, t_exec_pb <= T_frio_max (+1e-9, misma tolerancia
#     que opp_v5_2_split/opp_hc_4/opp_aco_4).
# y toma de opp_v5_2_split dos mejoras de formulacion que no cambian el problema:
# objetivo sobre v_b (no sobre v_pb de todos los pares) y filas de
# tardanza/adelanto solo para pares (n,b) con Bn = 1.
# Con V_p = 1 para todos los pickers y T_frio_max muy grande (defaults que
# escribe dat_files_builder cuando el escenario no los define) el modelo se
# reduce al problema original de opp_v4.
#
# Supuestos LP (del PDF "Supuestos de la Programacion Lineal"):
#   Proporcionalidad : cada termino de la FO y restricciones es lineal en sus vars.
#   Aditividad       : FO y restricciones son combinaciones lineales (sin productos
#                      entre variables de decision).
#   Divisibilidad    : variables continuas (ta, ea, t_exec, u_pb, v_pb, v_b, f)
#                      pueden tomar cualquier valor real >= 0.
#   Certeza          : todos los parametros (distancias, capacidades, pesos,
#                      fechas) son conocidos y fijos.
##############################################################################


##############################################################################
# SETS
##############################################################################

# N : ordenes de clientes
set N := { read "../dat_files/data_N.dat" as "<1s>" comment "#" };

# V : locaciones totales del almacen (incluye v_1 y v_f)
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
param v_1 := read "../dat_files/depot.dat"  as "1s" comment "#";   # deposito inicial
param v_f := read "../dat_files/final.dat"  as "1s" comment "#";   # nodo final

# Pesos de la funcion objetivo
param W_full    := read "../dat_files/params.dat" as "1n" skip 0 comment "#";  # peso tiempo cumplimiento
param W_ea_ta   := read "../dat_files/params.dat" as "1n" skip 1 comment "#";  # peso penalizaciones (adelanto + demora)
param W_ea      := read "../dat_files/params.dat" as "1n" skip 2 comment "#";  # peso adelanto (gamma)
param W_ta      := read "../dat_files/params.dat" as "1n" skip 3 comment "#";  # peso demora  (delta)

# Parametros de tiempo
param B_time    := read "../dat_files/params.dat" as "1n" skip 4 comment "#";  # tiempo por unidad de distancia
param B_setup   := read "../dat_files/params.dat" as "1n" skip 5 comment "#";  # tiempo de setup por lote
param B_picking := read "../dat_files/params.dat" as "1n" skip 6 comment "#";  # tiempo de picking por unidad de capacidad

# Capacidades --> NO USADO EN ESTE MODELO.
# param C_v       := read "../dat_files/params.dat" as "1n" skip 7 comment "#";  # capacidad del vehiculo de picking

# Big-M
param M         := read "../dat_files/params.dat" as "1n" skip 8 comment "#";  # entero suficientemente grande

# V_p[p] : factor de velocidad del picker p (1.0 = referencia; >1 = mas rapido)
param V_p[P]    := read "../dat_files/velocities.dat" as "<1s> 2n" comment "#";

# T_frio_max : tiempo maximo (mismas unidades que t_exec) que un lote puede
#              estar fuera de la camara de frio durante el armado
param T_frio_max := read "../dat_files/frio.dat" as "1n" comment "#";

# C_n[n] : capacidad requerida para la orden n
param C_n[N]    := read "../dat_files/cap_n.dat"      as "<1s> 2n" comment "#";

# Dd[n] : fecha limite (due date) de la orden n
param Dd[N]     := read "../dat_files/due_date.dat"   as "<1s> 2n" comment "#";

# d_ij[(i,j)] : distancia entre locaciones i y j  (solo arcos validos)
param d_ij[E]   := read "../dat_files/distances.dat"  as "<1s,2s> 3n" comment "#";

# S_i[i] : tiempo de servicio en la locacion i
param S_i[V]    := read "../dat_files/service_time.dat" as "<1s> 2n" comment "#";

# A_ni[n,i] : 1 si la orden n debe visitar la locacion i, 0 si no
param A_ni[N * V] := read "../dat_files/a_ni.dat"    as "<1s,2s> 3n" comment "#";

# Bn[n,b] : 1 si el lote b contiene la orden n, 0 si no
param Bn[N * B] := read "../dat_files/Bn.dat"        as "<1s,2s> 3n" comment "#";

# R_b[b] : numero de locaciones distintas requeridas por el lote b
#          (parametro derivado; R_b = |{i in V\{v_1,v_f} : sum_n A_ni[n,i]*Bn[n,b] >= 1}|)
param R_b[<b> in B] :=
    sum <i> in V with (i != v_1 and i != v_f and (sum <n> in N : A_ni[n,i] * Bn[n,b]) >= 1) : 1;

# tiempo_fijo[b] : parte de la duracion del lote que NO depende de la ruta
#                  (setup + picking en si), por lo tanto tampoco del picker
param tiempo_fijo[<b> in B] :=
    B_setup + B_picking * (sum <n> in N: C_n[n] * Bn[n,b]);

# Parámetro Big-M local para las restricciones de secuenciación sin solapamiento
# (19)-(20). Antes era 100000: un valor tan grande frente a la escala real de
# v_pb/t_exec_pb (decenas-cientos) infla la fila numéricamente y hace que SCIP
# acepte como "optimal" soluciones que violan la restricción por ~0.1 unidades
# de tiempo (ver tests/opp_v4/functional/test_case_13 y test_case_14:
# solapamiento de picker detectado por assert_no_time_overlap). 500 ya cubre la
# escala de las instancias actuales manteniendo el margen necesario para que el
# presolve no recorte la variable. Mismo valor que stage2_scheduling.zpl de opp_v5_2_split.
param M_seq := 500;

##############################################################################
# VARIABLES
##############################################################################

# ta_n[n] : tardanza de la orden n  (continua >= 0)
var ta_n[N]         >= 0;

# ea_n[n] : adelanto de la orden n  (continua >= 0)
var ea_n[N]         >= 0;

# R_b_time[b] : tiempo de traslado + servicio de la ruta elegida para el lote b
#               (continua >= 0). Es el mismo concepto que exporta la Etapa 1 de
#               opp_v5_2_split; aca NO es dato sino que se decide junto con la ruta.
var R_b_time[B]     >= 0;

# v_b[b] : tiempo de completitud del lote b  (continua >= 0)
#          [nueva variable de la especificacion; representa el makespan agregado
#           del lote, independiente del picker]
var v_b[B]          >= 0;

# u_pb[p,b] : tiempo de procesamiento del lote b asignado al picker p
#             (variable del modelo v2; se conserva).
# La cota superior implementa la cadena de frio: si X_pb = 1, (15) obliga a
# u_pb >= t_exec_pb, asi que t_exec_pb <= T_frio_max (+1e-9, la misma
# tolerancia que PB_elig de stage2_scheduling.zpl); si X_pb = 0 la cota no
# restringe nada porque u_pb puede valer 0.
var u_pb[P * B]     >= 0 <= T_frio_max + 1e-9;

# v_pb[p,b] : tiempo de completitud del lote b del picker p
#             (variable del modelo v2; se conserva)
var v_pb[P * B]     >= 0;

# z_ijb[i,j,b] : 1 si el arco (i,j) esta incluido en el lote b  (binaria)
#var z_ijb[V * V * B]  binary;

# z_ijb[i,j,b] : 1 si el arco valido (i,j) esta incluido en el lote b --> redefinimos la variable para que considere solo arcos válidos
var z_ijb[E * B] binary;

# f_ijb[i,j,b] : unidades que pasan por el arco (i,j) en el lote b  (continua >= 0)
#var f_ijb[V * V * B]  >= 0;

# f_ijb[i,j,b] : unidades que pasan por el arco valido (i,j) en el lote b --> redefinimos la variable para que considere solo arcos válidos
var f_ijb[E * B] >= 0;

##############################################################################
# NUEVAS VARIABLES
##############################################################################

# X_pb[p,b] : 1 si el lote b es asignado al picker p
var X_pb[P * B] binary;

# Variable auxiliar para secuenciación (solo definida para pares únicos b < k)
var Z_bk[<b,k> in B * B with b < k] binary;

##############################################################################
# OBJECTIVE FUNCTION
#
# min  W_full * sum_b v_b[b]
#    + W_ea_ta * ( W_ea * sum_n ea_n[n]  +  W_ta * sum_n ta_n[n] )
#
# Nota: v_b se vincula a v_pb mediante las restricciones de completitud (ver
# abajo). Igual que en opp_v5_2_split, el objetivo suma la completitud de cada lote en
# el picker que lo ejecuta (no v_pb sobre todos los pares (p,b), donde un
# v_pb > 0 forzado en un par NO asignado se pagaria sin corresponder a ningun
# lote real).
##############################################################################

minimize obj:
      W_full  * (sum <b> in B: v_b[b])
    + W_ea_ta * (  W_ea * (sum <n> in N: ea_n[n])
                 + W_ta * (sum <n> in N: ta_n[n])
                );


##############################################################################
# CONSTRAINTS
##############################################################################

############################### Rutas de lote ################################

# (1) Cada lote sale una vez del depósito
subto start_from_depot:
  forall <b> in B:
      sum <i, j> in E with i == v_1:
          z_ijb[i, j, b] == 1;

# (2) Cada lote entra una vez al nodo final
subto finish_at_end:
   forall <b> in B:
       sum <i, j> in E with j == v_f:
           z_ijb[i, j, b] == 1;

# (3) No hay retorno al depósito inicial - Nueva constraint
subto no_inflow_depot:
    forall <b> in B:
        sum <i, j> in E with j == v_1 and v_1 != v_f:
            z_ijb[i, j, b] == 0;

# (4) No hay salida desde el nodo final - Nueva constraint
subto no_outflow_final:
    forall <b> in B:
        sum <i, j> in E with i == v_f and v_1 != v_f:
            z_ijb[i, j, b] == 0;

####################### Visita y conservación de flujo #######################

# (5) Entrada a locaciones requeridas
subto force_visit_inflow:
   forall <b> in B:
       forall <j> in V with j != v_1 and j != v_f:
           sum <i, j> in E:
               z_ijb[i, j, b]
           >= if (sum <n> in N: A_ni[n,j] * Bn[n,b]) >= 1 then 1 else 0 end;

# (6) Salida de locaciones requeridas
subto force_visit_outflow:
    forall <b> in B:
        forall <j> in V with j != v_1 and j != v_f:
            sum <j, i> in E:
                z_ijb[j, i, b]
            >= if (sum <n> in N: A_ni[n,j] * Bn[n,b]) >= 1 then 1 else 0 end;

# (7) Conservación en nodos intermedios
subto flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_1 and i != v_f:
            (sum <g, i> in E: z_ijb[g, i, b])
            - (sum <i, j> in E: z_ijb[i, j, b]) == 0;

# (8) A lo sumo un arco de entrada por nodo
subto one_input_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_1:
            sum <j, i> in E:
                z_ijb[j, i, b] <= 1;

# (9) A lo sumo un arco de salida por nodo
subto one_output_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_f:
            sum <i, j> in E:
                z_ijb[i, j, b] <= 1;

#################### Subtour elimination y flujo de carga ####################

# (10) Límite MTZ subtours
subto subtour_elimination_bound:
    forall <b> in B:
        forall <i, j> in E:
            f_ijb[i, j, b] - R_b[b] * z_ijb[i, j, b] <= 0;

# (11) Flujo total desde el depósito
subto f_depot_source:
    forall <b> in B:
        sum <i, j> in E with i == v_1:
            f_ijb[i, j, b] == R_b[b];

# (12) Balance Gavish-Graves
subto f_flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_1 and i != v_f:
            (sum <g, i> in E: f_ijb[g, i, b])
            - (sum <i, j> in E: f_ijb[i, j, b])
            == if (sum <n> in N: A_ni[n,i] * Bn[n,b]) >= 1 then 1 else 0 end;

##################### Tiempo de ejecución y completitud ######################

# (13) Tiempo de ruta del lote (traslado + servicio)
# El termino S_i se agrega respecto al modelo v2 original.
# R_b_time[b] = traslado (distancia * B_time) + servicio en cada ubicacion
# visitada. NO incluye B_setup ni B_picking (ver tiempo_fijo): esos no dependen
# de la ruta. Es la misma definicion que define_route_time de
# stage1_routing.zpl (opp_v5_2_split); la unica diferencia es que aca la ruta y su
# tiempo se deciden en el mismo MIP que la asignacion y la secuenciacion.
subto define_route_time:
    forall <b> in B:
        R_b_time[b] ==
              B_time    * (sum <i,j> in E with i != v_f and j != v_1:
                               d_ij[i,j] * z_ijb[i,j,b])
            + (sum <i> in V with i != v_1 and i != v_f:
                   S_i[i] * (sum <i, j> in E: z_ijb[i, j, b]));

#################### Asignación de lotes y secuenciación #####################

# (14) Asignación única por lote a un picker - Nueva constraint
subto assign_exactly_one_picker:
    forall <b> in B:
        sum <p> in P: X_pb[p,b] == 1;

# (15) Ejecución acota procesamiento (cota inferior)
# t_exec_pb = tiempo_fijo[b] + R_b_time[b] / V_p[p]  (solo la ruta escala con la
# velocidad del picker, igual que t_exec_pb de stage2_scheduling.zpl).
#   tiempo_fijo[b] + R_b_time[b]/V_p[p] - M * (1 - X_pb[p,b]) <= u_pb[p,b]
subto batch_execution_time:
    forall <p,b> in P * B:
        tiempo_fijo[b] + R_b_time[b] / V_p[p] - M * (1 - X_pb[p,b]) <= u_pb[p,b];

# (16) cota superior; fija u_pb = t_exec_pb cuando X_pb=1
subto batch_execution_time_upper:
    forall <p,b> in P * B:
        u_pb[p,b] <= tiempo_fijo[b] + R_b_time[b] / V_p[p] + M * (1 - X_pb[p,b]);

# (17) Procesamiento precede a completitud
subto processing_le_completion:
    forall <p,b> in P * B:
        u_pb[p,b] <= v_pb[p,b];

# (18) Completitud del lote vs picker
# v_b[b] se define como el maximo de v_pb[p,b] sobre los pickers que tienen
# asignado el lote b.  Se linealiza como:
#   v_pb[p,b] - M * (1 - X_pb[p,b]) <= v_b[b]   forall p, b
subto v_b_lower_bound:
    forall <p,b> in P * B:
        v_pb[p,b] - M * (1 - X_pb[p,b]) <= v_b[b];

###################### Secuenciamiento sin solapamiento ######################

# (19) Secuenciamiento sin solapamiento (orden 1) - Nueva constraint
# Si ambos lotes se asignan al mismo picker, uno debe ejecutarse después del otro.
# La duracion del lote k depende del picker p (velocidad V_p[p]), igual que
# t_exec_pb[p,k] en stage2_scheduling.zpl.
subto non_overlap_1:
    forall <p> in P:
        forall <b, k> in B * B with b < k:
            v_pb[p,k] >= v_pb[p,b] + tiempo_fijo[k] + R_b_time[k] / V_p[p]
                         - M_seq * (3 - X_pb[p,b] - X_pb[p,k] - Z_bk[b,k]);

# (20) Secuenciamiento sin solapamiento (orden 2) - Nueva constraint
subto non_overlap_2:
    forall <p> in P:
        forall <b, k> in B * B with b < k:
            v_pb[p,b] >= v_pb[p,k] + tiempo_fijo[b] + R_b_time[b] / V_p[p]
                         - M_seq * (2 - X_pb[p,b] - X_pb[p,k] + Z_bk[b,k]);

########################### Earliness y tardiness ############################

# Filtradas por Bn[n,b] == 1 (igual que stage2_scheduling.zpl): para un par
# (n,b) con Bn = 0 la restriccion nunca es activa (M es cota valida), asi que
# generarla solo agrega filas.

# (21) Definición de tardanza
# v_pb[p,b] - Dd[n] - M * (2 - X_pb[p,b] - Bn[n,b]) <= ta_n[n]
subto tardiness_definition:
    forall <p,b,n> in P * B * N with Bn[n,b] == 1:
        v_pb[p,b] - Dd[n] - M * (2 - X_pb[p,b] - Bn[n,b]) <= ta_n[n];

# (22) Definición de adelanto
# Dd[n] - v_pb[p,b] - M * (2 - X_pb[p,b] - Bn[n,b]) <= ea_n[n]
subto earliness_definition:
    forall <p,b,n> in P * B * N with Bn[n,b] == 1:
        Dd[n] - v_pb[p,b] - M * (2 - X_pb[p,b] - Bn[n,b]) <= ea_n[n];

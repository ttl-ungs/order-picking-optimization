##############################################################################
# OPP Model V4 - ZIMPL Formulation
# Basado en: OPPModelV2 (opp_model_v2.py) y models.pdf (Segunda Version).
# Modelo con asignación de lotes a pickers.
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
param W_full    := read "../dat_files/params.dat" as "1n" use 1 comment "#";  # peso tiempo cumplimiento
param W_ea_ta   := read "../dat_files/params.dat" as "1n" use 2 comment "#";  # peso penalizaciones (adelanto + demora)
param W_ea      := read "../dat_files/params.dat" as "1n" use 3 comment "#";  # peso adelanto (gamma)
param W_ta      := read "../dat_files/params.dat" as "1n" use 4 comment "#";  # peso demora  (delta)

# Parametros de tiempo
param B_time    := read "../dat_files/params.dat" as "1n" use 5 comment "#";  # tiempo por unidad de distancia
param B_setup   := read "../dat_files/params.dat" as "1n" use 6 comment "#";  # tiempo de setup por lote
param B_picking := read "../dat_files/params.dat" as "1n" use 7 comment "#";  # tiempo de picking por unidad de capacidad

# Capacidades
param C_v       := read "../dat_files/params.dat" as "1n" use 8 comment "#";  # capacidad del vehiculo de picking

# Big-M
param M         := read "../dat_files/params.dat" as "1n" use 9 comment "#";  # entero suficientemente grande

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


##############################################################################
# VARIABLES
##############################################################################

# ta_n[n] : tardanza de la orden n  (continua >= 0)
var ta_n[N]         >= 0;

# ea_n[n] : adelanto de la orden n  (continua >= 0)
var ea_n[N]         >= 0;

# t_exec_b[b] : tiempo de ejecucion del lote b  (continua >= 0)
var t_exec_b[B]     >= 0;

# v_b[b] : tiempo de completitud del lote b  (continua >= 0)
#          [nueva variable de la especificacion; representa el makespan agregado
#           del lote, independiente del picker]
var v_b[B]          >= 0;

# u_pb[p,b] : tiempo de procesamiento del lote b asignado al picker p
#             (variable del modelo v2; se conserva)
var u_pb[P * B]     >= 0;

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

##############################################################################
# OBJECTIVE FUNCTION
#
# min  W_full * sum_{p,b} v_pb[p,b]
#    + W_ea_ta * ( W_ea * sum_n ea_n[n]  +  W_ta * sum_n ta_n[n] )
#
# Nota: v_b se vincula a v_pb mediante las restricciones de completitud (ver abajo).
##############################################################################

minimize obj:
      W_full  * (sum <p,b> in P * B: v_pb[p,b])
    + W_ea_ta * (  W_ea * (sum <n> in N: ea_n[n])
                 + W_ta * (sum <n> in N: ta_n[n])
                );


##############################################################################
# CONSTRAINTS
##############################################################################

# (6) La ruta del lote b sale exactamente una vez del deposito
subto start_from_depot:
  forall <b> in B:
      sum <i, j> in E with i == v_1:
          z_ijb[i, j, b] == 1;

# (7) La ruta del lote b entra exactamente una vez al nodo final
subto finish_at_end:
   forall <b> in B:
       sum <i, j> in E with j == v_f:
           z_ijb[i, j, b] == 1;

# (10) Si una locacion es requerida por el lote, debe tener arco entrante
subto force_visit_inflow:
   forall <b> in B:
       forall <j> in V with j != v_1 and j != v_f:
           sum <i, j> in E:
               z_ijb[i, j, b]
           >= if (sum <n> in N: A_ni[n,j] * Bn[n,b]) >= 1 then 1 else 0 end;

# (11) Si una locacion es requerida por el lote, debe tener arco saliente
subto force_visit_outflow:
    forall <b> in B:
        forall <j> in V with j != v_1 and j != v_f:
            sum <j, i> in E:
                z_ijb[j, i, b]
            >= if (sum <n> in N: A_ni[n,j] * Bn[n,b]) >= 1 then 1 else 0 end;

# (12) Cota de ruteo MTZ
subto subtour_elimination_bound:
    forall <b> in B:
        forall <i, j> in E:
            f_ijb[i, j, b] - R_b[b] * z_ijb[i, j, b] <= 0;

# (13) Conservacion de flujo en la ruta (nodos intermedios)
subto flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_1 and i != v_f:
            (sum <g, i> in E: z_ijb[g, i, b])
            - (sum <i, j> in E: z_ijb[i, j, b]) == 0;

# (14) A lo sumo un arco de entrada por nodo (excepto deposito)
subto one_input_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_1:
            sum <j, i> in E:
                z_ijb[j, i, b] <= 1;

# (15) A lo sumo un arco de salida por nodo (excepto nodo final)
subto one_output_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_f:
            sum <i, j> in E:
                z_ijb[i, j, b] <= 1;

# (16a) Gavish-Graves: flujo total desde el deposito == R_b[b]
subto f_depot_source:
    forall <b> in B:
        sum <i, j> in E with i == v_1:
            f_ijb[i, j, b] == R_b[b];

# (16b) Gavish-Graves: balance de flujo en nodos intermedios
subto f_flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_1 and i != v_f:
            (sum <g, i> in E: f_ijb[g, i, b])
            - (sum <i, j> in E: f_ijb[i, j, b])
            == if (sum <n> in N: A_ni[n,i] * Bn[n,b]) >= 1 then 1 else 0 end;

# (18) Tiempo de ejecucion del lote
# El termino S_i se agrega respecto al modelo v2 original
subto valid_execution_time:
    forall <b> in B:
        t_exec_b[b] >=
              B_setup
            + B_picking * (sum <n> in N: C_n[n] * Bn[n,b])
            + B_time    * (sum <i,j> in E with i != v_f and j != v_1:
                               d_ij[i,j] * z_ijb[i,j,b])
             + (sum <i> in V with i != v_1 and i != v_f:
                   S_i[i] * (sum <i, j> in E: z_ijb[i, j, b]));

# (19) t_exec_b acota u_pb por picker
# t_exec_b[b] - M * (1 - X_pb[p,b]) <= u_pb[p,b]
subto batch_execution_time:
    forall <p,b> in P * B:
        t_exec_b[b] - M * (1 - X_pb[p,b]) <= u_pb[p,b];

# (20) u_pb <= v_pb  (procesamiento <= completitud por picker)
subto processing_le_completion:
    forall <p,b> in P * B:
        u_pb[p,b] <= v_pb[p,b];

# (20b) v_b vinculada a v_pb
# v_b[b] se define como el maximo de v_pb[p,b] sobre los pickers que tienen
# asignado el lote b.  Se linealiza como:
#   v_pb[p,b] - M * (1 - X_pb[p,b]) <= v_b[b]   forall p, b
subto v_b_lower_bound:
    forall <p,b> in P * B:
        v_pb[p,b] - M * (1 - X_pb[p,b]) <= v_b[b];

# (22) Definicion de tardanza
# v_pb[p,b] - Dd[n] - M * (2 - X_pb[p,b] - Bn[n,b]) <= ta_n[n]
subto tardiness_definition:
    forall <p,b,n> in P * B * N:
        v_pb[p,b] - Dd[n] - M * (2 - X_pb[p,b] - Bn[n,b]) <= ta_n[n];

# (23) Definicion de adelanto
# Dd[n] - v_pb[p,b] - M * (2 - X_pb[p,b] - Bn[n,b]) <= ea_n[n]
subto earliness_definition:
    forall <p,b,n> in P * B * N:
        Dd[n] - v_pb[p,b] - M * (2 - X_pb[p,b] - Bn[n,b]) <= ea_n[n];

##############################################################################
# NUEVAS CONSTRAINTS
##############################################################################

# (A1) Asignación única: Cada lote debe estar asignado a exactamente un picker
subto assign_exactly_one_picker:
    forall <b> in B:
        sum <p> in P: X_pb[p,b] == 1;

# Variable auxiliar para secuenciación (solo definida para pares únicos b < k)
var Z_bk[<b,k> in B * B with b < k] binary;

# Parámetro Big-M local gigante para evitar cortes de presolve en variables continuas
param M_seq := 100000;

# (A2) Secuenciamiento sin solapamiento
# Si ambos lotes se asignan al mismo picker, uno debe ejecutarse después del otro.
subto non_overlap_1:
    forall <p> in P:
        forall <b, k> in B * B with b < k:
            v_pb[p,k] >= v_pb[p,b] + t_exec_b[k] - M_seq * (3 - X_pb[p,b] - X_pb[p,k] - Z_bk[b,k]);

subto non_overlap_2:
    forall <p> in P:
        forall <b, k> in B * B with b < k:
            v_pb[p,b] >= v_pb[p,k] + t_exec_b[b] - M_seq * (2 - X_pb[p,b] - X_pb[p,k] + Z_bk[b,k]);
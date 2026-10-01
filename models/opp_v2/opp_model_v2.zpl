##############################################################################
# OPP Model V2 - ZIMPL Formulation
# Basado en: OPPModelV2 (opp_model_v2.py) y models.pdf (Segunda Version)
#
# Supuestos LP (del PDF "Supuestos de la Programacion Lineal"):
#   Proporcionalidad : cada termino de la FO y restricciones es lineal en sus vars.
#   Aditividad       : FO y restricciones son combinaciones lineales (sin productos
#                      entre variables de decision).
#   Divisibilidad    : variables continuas (ta, ea, t_exec, u_pb, c_pb, c_b, f)
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
param v_start := read "../dat_files/depot.dat"  as "1s" comment "#";   # deposito inicial
param v_end := read "../dat_files/final.dat"  as "1s" comment "#";   # nodo final

# Pesos de la funcion objetivo
param W_c    := read "../dat_files/params.dat" as "1n" use 1 comment "#";  # peso tiempo cumplimiento
param W_pen   := read "../dat_files/params.dat" as "1n" use 2 comment "#";  # peso penalizaciones (adelanto + demora)
param W_e      := read "../dat_files/params.dat" as "1n" use 3 comment "#";  # peso adelanto (gamma)
param W_t      := read "../dat_files/params.dat" as "1n" use 4 comment "#";  # peso demora  (delta)

# Parametros de tiempo
param T_travel    := read "../dat_files/params.dat" as "1n" use 5 comment "#";  # tiempo por unidad de distancia
param T_setup   := read "../dat_files/params.dat" as "1n" use 6 comment "#";  # tiempo de setup por lote
param T_pick := read "../dat_files/params.dat" as "1n" use 7 comment "#";  # tiempo de picking por unidad de capacidad

# Capacidades
param C_v       := read "../dat_files/params.dat" as "1n" use 8 comment "#";  # capacidad del vehiculo de picking

# Big-M
param M         := read "../dat_files/params.dat" as "1n" use 9 comment "#";  # entero suficientemente grande

# C_n[n] : capacidad requerida para la orden n
param C_n[N]    := read "../dat_files/cap_n.dat"      as "<1s> 2n" comment "#";

# T_due_n[n] : fecha limite (due date) de la orden n
param T_due_n[N]     := read "../dat_files/due_date.dat"   as "<1s> 2n" comment "#";

# D_ij[(i,j)] : distancia entre locaciones i y j  (solo arcos validos)
param D_ij[E]   := read "../dat_files/distances.dat"  as "<1s,2s> 3n" comment "#";

# S_i[i] : tiempo de servicio en la locacion i
param S_i[V]    := read "../dat_files/service_time.dat" as "<1s> 2n" comment "#";

# A_ni[n,i] : 1 si la orden n debe visitar la locacion i, 0 si no
param A_ni[N * V] := read "../dat_files/a_ni.dat"    as "<1s,2s> 3n" comment "#";

# B_nb[n,b] : 1 si el lote b contiene la orden n, 0 si no
param B_nb[N * B] := read "../dat_files/B_nb.dat"        as "<1s,2s> 3n" comment "#";

# X_pb[p,b] : 1 si el lote b es asignado al picker p  (parametro de entrada)
param X_pb[P * B] := read "../dat_files/x_pb.dat"   as "<1s,2s> 3n" comment "#";

# L_b[b] : numero de locaciones distintas requeridas por el lote b
#          (parametro derivado; L_b = |{i in V\{v_start,v_end} : sum_n A_ni[n,i]*B_nb[n,b] >= 1}|)
param L_b[<b> in B] :=
    sum <i> in V with (i != v_start and i != v_end and (sum <n> in N : A_ni[n,i] * B_nb[n,b]) >= 1) : 1;


##############################################################################
# VARIABLES
##############################################################################

# ta_n[n] : tardanza de la orden n  (continua >= 0)
var ta_n[N]         >= 0;

# ea_n[n] : adelanto de la orden n  (continua >= 0)
var ea_n[N]         >= 0;

# d_b[b] : tiempo de ejecucion del lote b  (continua >= 0)
var d_b[B]     >= 0;

# c_b[b] : tiempo de completitud del lote b  (continua >= 0)
#          [nueva variable de la especificacion; representa el makespan agregado
#           del lote, independiente del picker]
var c_b[B]          >= 0;

# u_pb[p,b] : tiempo de procesamiento del lote b asignado al picker p
#             (variable del modelo v2; se conserva)
var u_pb[P * B]     >= 0;

# c_pb[p,b] : tiempo de completitud del lote b del picker p
#             (variable del modelo v2; se conserva)
var c_pb[P * B]     >= 0;

# z_ijb[i,j,b] : 1 si el arco (i,j) esta incluido en el lote b  (binaria)
#var z_ijb[V * V * B]  binary;

# z_ijb[i,j,b] : 1 si el arco valido (i,j) esta incluido en el lote b --> redefinimos la variable para que considere solo arcos válidos
var z_ijb[E * B] binary;

# q_ijb[i,j,b] : unidades que pasan por el arco (i,j) en el lote b  (continua >= 0)
#var q_ijb[V * V * B]  >= 0;

# q_ijb[i,j,b] : unidades que pasan por el arco valido (i,j) en el lote b --> redefinimos la variable para que considere solo arcos válidos
var q_ijb[E * B] >= 0;


##############################################################################
# OBJECTIVE FUNCTION
#
# min  W_c * sum_{p,b} c_pb[p,b]
#    + W_pen * ( W_e * sum_n ea_n[n]  +  W_t * sum_n ta_n[n] )
#
# Nota: c_b se vincula a c_pb mediante las restricciones de completitud (ver abajo).
##############################################################################

minimize obj:
      W_c  * (sum <p,b> in P * B: c_pb[p,b])
    + W_pen * (  W_e * (sum <n> in N: ea_n[n])
                 + W_t * (sum <n> in N: ta_n[n])
                );


##############################################################################
# CONSTRAINTS
##############################################################################

# (6) La ruta del lote b sale exactamente una vez del deposito
subto start_from_depot:
  forall <b> in B:
      sum <v_start, j> in E:
          z_ijb[v_start, j, b] == 1;

# (7) La ruta del lote b entra exactamente una vez al nodo final
subto finish_at_end:
   forall <b> in B:
       sum <i, v_end> in E:
           z_ijb[i, v_end, b] == 1;

# (8) No se puede volver al deposito --> ya no hace falta por cómo están definidos los arcos
#subto cant_go_back_to_depot:
 #   forall <b> in B:
  #      sum <i> in V with i != v_start:
   #         z_ijb[i, v_start, b] == 0;

# (9) No se puede salir del nodo final --> ya no hace falta por cómo están definidos los arcos
#subto cant_move_from_end_node:
 #   forall <b> in B:
  #      sum <j> in V with j != v_end:
   #         z_ijb[v_end, j, b] == 0;

# (10) Si una locacion es requerida por el lote, debe tener arco entrante
subto force_visit_inflow:
   forall <b> in B:
       forall <j> in V with j != v_start and j != v_end:
           sum <i, j> in E:
               z_ijb[i, j, b]
           >= if (sum <n> in N: A_ni[n,j] * B_nb[n,b]) >= 1 then 1 else 0 end;

# (11) Si una locacion es requerida por el lote, debe tener arco saliente
subto force_visit_outflow:
    forall <b> in B:
        forall <j> in V with j != v_start and j != v_end:
            sum <j, i> in E:
                z_ijb[j, i, b]
            >= if (sum <n> in N: A_ni[n,j] * B_nb[n,b]) >= 1 then 1 else 0 end;

# (12) Capacidad de articulos: q_ijb <= C_v * z_ijb
subto articles_capacity:
    forall <b> in B:
        forall <i, j> in E:
            q_ijb[i, j, b] - C_v * z_ijb[i, j, b] <= 0;

# (13) Conservacion de flujo en la ruta (nodos intermedios)
subto route_flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_start and i != v_end:
            (sum <g, i> in E: z_ijb[g, i, b])
            - (sum <i, j> in E: z_ijb[i, j, b]) == 0;

# (14) A lo sumo un arco de entrada por nodo (excepto deposito)
subto one_input_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_start:
            sum <j, i> in E:
                z_ijb[j, i, b] <= 1;

# (15) A lo sumo un arco de salida por nodo (excepto nodo final)
subto one_output_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_end:
            sum <i, j> in E:
                z_ijb[i, j, b] <= 1;

# (16a) Gavish-Graves: flujo total desde el deposito == L_b[b]
subto load_flow_source:
    forall <b> in B:
        sum <v_start, j> in E:
            q_ijb[v_start, j, b] == L_b[b];

# (16b) Gavish-Graves: balance de flujo en nodos intermedios
subto load_flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_start and i != v_end:
            (sum <g, i> in E: q_ijb[g, i, b])
            - (sum <i, j> in E: q_ijb[i, j, b])
            == if (sum <n> in N: A_ni[n,i] * B_nb[n,b]) >= 1 then 1 else 0 end;

# (17) Sin loops: z_ijb[i,i,b] = 0  (i != v_start) --> ya no hace falta por cómo están definidos los arcos
#subto no_loops:
 #   forall <b> in B:
  #      forall <i> in V with i != v_start:
   #         z_ijb[i, i, b] == 0;

# (18) Tiempo de ejecucion del lote
# El termino S_i se agrega respecto al modelo v2 original
subto valid_execution_time:
    forall <b> in B:
        d_b[b] >=
              T_setup
            + T_pick * (sum <n> in N: C_n[n] * B_nb[n,b])
            + T_travel    * (sum <i,j> in E with i != v_end and j != v_start:
                               D_ij[i,j] * z_ijb[i,j,b])
             + (sum <i> in V with i != v_start and i != v_end:
                   S_i[i] * (sum <i, j> in E: z_ijb[i, j, b]));

# (19) d_b acota u_pb por picker
# d_b[b] - M * (1 - X_pb[p,b]) <= u_pb[p,b]
subto batch_execution_time:
    forall <p,b> in P * B:
        d_b[b] - M * (1 - X_pb[p,b]) <= u_pb[p,b];

# (20) u_pb <= c_pb  (procesamiento <= completitud por picker)
subto processing_le_completion:
    forall <p,b> in P * B:
        u_pb[p,b] <= c_pb[p,b];

# (20b) c_b vinculada a c_pb
# c_b[b] se define como el maximo de c_pb[p,b] sobre los pickers que tienen
# asignado el lote b.  Se linealiza como:
#   c_pb[p,b] - M * (1 - X_pb[p,b]) <= c_b[b]   forall p, b
subto v_b_lower_bound:
    forall <p,b> in P * B:
        c_pb[p,b] - M * (1 - X_pb[p,b]) <= c_b[b];

# (22) Definicion de tardanza
# c_pb[p,b] - T_due_n[n] - M * (2 - X_pb[p,b] - B_nb[n,b]) <= ta_n[n]
subto tardiness_definition:
    forall <p,b,n> in P * B * N:
        c_pb[p,b] - T_due_n[n] - M * (2 - X_pb[p,b] - B_nb[n,b]) <= ta_n[n];

# (23) Definicion de adelanto
# T_due_n[n] - c_pb[p,b] - M * (2 - X_pb[p,b] - B_nb[n,b]) <= ea_n[n]
subto earliness_definition:
    forall <p,b,n> in P * B * N:
        T_due_n[n] - c_pb[p,b] - M * (2 - X_pb[p,b] - B_nb[n,b]) <= ea_n[n];

# (24) Capacidad del lote: sum_n C_n[n] * B_nb[n,b] <= C_v --> comentada porque no tiene que ver con nada que optimice el modelo, tiene que haber una validación en el dto
#subto batch_capacity:
 #   forall <b> in B:
  #      sum <n> in N: C_n[n] * B_nb[n,b] <= C_v; #!

# (25) Solo arcos validos del grafo: z_ijb = 0 si (i,j) not in E --> ya no hace falta por cómo están definidos los arcos
#subto only_valid_edges:
 #   forall <b> in B:
  #      forall <i,j> in V * V with (i,j) not in E:
   #         z_ijb[i, j, b] == 0;

##############################################################################
# OPP Model - ETAPA 1: Ruteo por lote (independiente del picker)
#
# Como ningun termino de ruteo depende de que picker ejecuta el
# lote ni del orden entre lotes, el ruteo optimo de cada lote b se puede
# resolver de forma totalmente independiente de la asignacion/secuenciacion.
# Este modelo resuelve, para TODOS los lotes a la vez (no interactuan entre
# si), el camino de menor tiempo (traslado + atencion en cada ubicacion)
# que visita las ubicaciones requeridas del lote.
#
# Salida para la Etapa 2: r_b[b], el tiempo de traslado+servicio
# del lote b bajo la mejor ruta posible (todavia SIN aplicar velocidad de
# picker ni tiempos de setup/picking, que son independientes de la ruta).
##############################################################################


##############################################################################
# SETS
##############################################################################

# N : ordenes de clientes
set N := { read "../dat_files/data_N.dat" as "<1s>" comment "#" };

# V : locaciones totales del almacen (incluye v_start y v_end)
set V := { read "../dat_files/data_V.dat" as "<1s>" comment "#" };

# B : lotes de pedidos factibles
set B := { read "../dat_files/data_B.dat" as "<1s>" comment "#" };

# E : arcos validos del grafo de locaciones
set E := { read "../dat_files/data_E.dat" as "<1s,2s>" comment "#" };


##############################################################################
# PARAMETERS
##############################################################################

# v_start / v_end : nodo de inicio (deposito) y nodo final de cada ruta
param v_start := read "../dat_files/depot.dat" as "1s" comment "#";
param v_end   := read "../dat_files/final.dat" as "1s" comment "#";

# T_travel : tiempo por unidad de distancia
param T_travel := read "../dat_files/params.dat" as "1n" skip 4 comment "#";

# D_ij[(i,j)] : distancia entre locaciones i y j (solo arcos validos)
param D_ij[E] := read "../dat_files/distances.dat" as "<1s,2s> 3n" comment "#";

# S_i[i] : tiempo de servicio en la locacion i
param S_i[V] := read "../dat_files/service_time.dat" as "<1s> 2n" comment "#";

# A_ni[n,i] : 1 si la orden n debe visitar la locacion i, 0 si no
param A_ni[N * V] := read "../dat_files/a_ni.dat" as "<1s,2s> 3n" comment "#";

# B_nb[n,b] : 1 si el lote b contiene la orden n, 0 si no
param B_nb[N * B] := read "../dat_files/B_nb.dat" as "<1s,2s> 3n" comment "#";

# L_b[b] : numero de locaciones distintas requeridas por el lote b (para GG)
param L_b[<b> in B] :=
    sum <i> in V with (i != v_start and i != v_end and (sum <n> in N : A_ni[n,i] * B_nb[n,b]) >= 1) : 1;


##############################################################################
# VARIABLES
##############################################################################

# z_ijb[i,j,b] : 1 si el arco valido (i,j) esta incluido en el lote b
var z_ijb[E * B] binary;

# q_ijb[i,j,b] : flujo de carga de Gavish-Graves: cantidad de locaciones
#                requeridas del lote b que todavia faltan visitar al recorrer
#                el arco valido (i,j). Solo existe para eliminar subtours.
var q_ijb[E * B] >= 0;

# r_b[b] : tiempo de traslado + servicio del lote b bajo la mejor ruta
#               (esto es lo que se exporta a la Etapa 2)
var r_b[B] >= 0;


##############################################################################
# OBJECTIVE
#
# Como los lotes no interactuan entre si, minimizar la suma es equivalente
# a minimizar cada r_b[b] por separado.
##############################################################################

minimize obj:
    sum <b> in B: r_b[b];


##############################################################################
# CONSTRAINTS
##############################################################################

############################### Rutas de lote ################################

subto start_from_depot:
    forall <b> in B:
        sum <i, j> in E with i == v_start:
            z_ijb[i, j, b] == 1;

subto finish_at_end:
    forall <b> in B:
        sum <i, j> in E with j == v_end:
            z_ijb[i, j, b] == 1;

subto no_inflow_depot:
    forall <b> in B:
        sum <i, j> in E with j == v_start and v_start != v_end:
            z_ijb[i, j, b] == 0;

subto no_outflow_final:
    forall <b> in B:
        sum <i, j> in E with i == v_end and v_start != v_end:
            z_ijb[i, j, b] == 0;

####################### Visita y conservacion de flujo #######################

subto force_visit_inflow:
    forall <b> in B:
        forall <j> in V with j != v_start and j != v_end:
            sum <i, j> in E:
                z_ijb[i, j, b]
            >= if (sum <n> in N: A_ni[n,j] * B_nb[n,b]) >= 1 then 1 else 0 end;

subto force_visit_outflow:
    forall <b> in B:
        forall <j> in V with j != v_start and j != v_end:
            sum <j, i> in E:
                z_ijb[j, i, b]
            >= if (sum <n> in N: A_ni[n,j] * B_nb[n,b]) >= 1 then 1 else 0 end;

subto route_flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_start and i != v_end:
            (sum <g, i> in E: z_ijb[g, i, b])
            - (sum <i, j> in E: z_ijb[i, j, b]) == 0;

subto one_input_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_start:
            sum <j, i> in E:
                z_ijb[j, i, b] <= 1;

subto one_output_arc_per_node:
    forall <b> in B:
        forall <i> in V with i != v_end:
            sum <i, j> in E:
                z_ijb[i, j, b] <= 1;

#################### Subtour elimination y flujo de carga ####################

subto load_flow_bound:
    forall <b> in B:
        forall <i, j> in E:
            q_ijb[i, j, b] - L_b[b] * z_ijb[i, j, b] <= 0;

subto load_flow_source:
    forall <b> in B:
        sum <i, j> in E with i == v_start:
            q_ijb[i, j, b] == L_b[b];

subto load_flow_conservation:
    forall <b> in B:
        forall <i> in V with i != v_start and i != v_end:
            (sum <g, i> in E: q_ijb[g, i, b])
            - (sum <i, j> in E: q_ijb[i, j, b])
            == if (sum <n> in N: A_ni[n,i] * B_nb[n,b]) >= 1 then 1 else 0 end;

########################## Tiempo de ruta del lote ############################

# r_b[b] = traslado (distancia * T_travel) + servicio en cada ubicacion
# visitada. NO incluye T_setup ni T_pick: esos son independientes de la
# ruta elegida (dependen solo de la composicion del lote), asi que no hace
# falta que el solver de la Etapa 1 los cargue - se suman en la Etapa 2.
subto define_route_time:
    forall <b> in B:
        r_b[b] ==
              T_travel * (sum <i,j> in E with i != v_end and j != v_start:
                             D_ij[i,j] * z_ijb[i,j,b])
            + (sum <i> in V with i != v_start and i != v_end:
                   S_i[i] * (sum <i, j> in E: z_ijb[i, j, b]));

##############################################################################
# OPP Model - ETAPA 2: Asignacion + secuenciacion + cadena de frio
#
# Recibe como dato el resultado de la Etapa 1 (tiempo de ruta por lote,
# R_b[b]) y ya NO decide nada sobre el ruteo: aca solo se decide que
# picker hace cada lote, en que orden, y se controla tardanza/adelanto y el
# limite de tiempo fuera de frio.
#
# Novedades respecto al modelo original:
#   - Pickers heterogeneos por velocidad (V_p). Asumimos que la velocidad
#     escala el tiempo de traslado+servicio (R_b), pero NO el setup ni
#     el tiempo de picking en si (B_setup, B_picking), que se consideran
#     ligados a la tarea y no al desplazamiento. Si en la practica el
#     picking tambien depende de la destreza/velocidad del picker, esos
#     terminos se pueden mover dentro del numerador que se divide por V_p
#     sin romper nada de lo que sigue.
#   - t_exec_pb pasa de ser VARIABLE (con Big-M para linkearla) a ser un
#     PARAMETRO precalculado: al ser R_b[b] un dato fijo (ya optimizado
#     en la Etapa 1), t_exec_pb[p,b] = tiempo_fijo[b] + R_b[b]/V_p[p]
#     es un numero conocido antes de resolver. Esto elimina la necesidad de
#     Big-M para linkear "tiempo de ejecucion" con "tiempo de procesamiento"
#     (ver comentario en batch_completion_floor) y elimina la variable u_pb.
#   - Restriccion dura de cadena de frio: un lote solo puede asignarse a un
#     picker si, a la velocidad de ESE picker, el lote se arma en menos de
#     T_frio_max. Se implementa restringiendo el dominio de las variables al
#     conjunto PB_elig, no como restriccion aparte.
##############################################################################


##############################################################################
# SETS
##############################################################################

set N := { read "../dat_files/data_N.dat" as "<1s>" comment "#" };
set P := { read "../dat_files/data_P.dat" as "<1s>" comment "#" };
set B := { read "../dat_files/data_B.dat" as "<1s>" comment "#" };


##############################################################################
# PARAMETERS - datos originales
##############################################################################

param W_full  := read "../dat_files/params.dat" as "1n" skip 0 comment "#";
param W_ea_ta := read "../dat_files/params.dat" as "1n" skip 1 comment "#";
param W_ea    := read "../dat_files/params.dat" as "1n" skip 2 comment "#";
param W_ta    := read "../dat_files/params.dat" as "1n" skip 3 comment "#";

param B_setup   := read "../dat_files/params.dat" as "1n" skip 5 comment "#";
param B_picking := read "../dat_files/params.dat" as "1n" skip 6 comment "#";

param M     := read "../dat_files/params.dat" as "1n" skip 8 comment "#";
param M_seq := read "../dat_files/params.dat" as "1n" skip 9 comment "#";

param C_n[N] := read "../dat_files/cap_n.dat"    as "<1s> 2n" comment "#";
param Dd[N]  := read "../dat_files/due_date.dat" as "<1s> 2n" comment "#";
param Bn[N * B] := read "../dat_files/Bn.dat"    as "<1s,2s> 3n" comment "#";

##############################################################################
# PARAMETERS - nuevos
##############################################################################

# R_b[b] : tiempo de traslado+servicio optimo del lote b (salida Etapa 1)
param R_b[B] := read "../dat_files/route_time_b.dat" as "<1s> 2n" comment "#";

# V_p[p] : factor de velocidad del picker p (1.0 = referencia; >1 = mas rapido)
param V_p[P] := read "../dat_files/velocities.dat" as "<1s> 2n" comment "#";

# T_frio_max : tiempo maximo (mismas unidades que t_exec) que un lote puede
#              estar fuera de la camara de frio durante el armado
param T_frio_max := read "../dat_files/frio.dat" as "1n" comment "#";

# tiempo_fijo[b] : parte de la duracion del lote que NO depende de la ruta
#                  (setup + picking en si), por lo tanto tampoco del picker
#                  bajo el supuesto de arriba
param tiempo_fijo[<b> in B] :=
    B_setup + B_picking * (sum <n> in N: C_n[n] * Bn[n,b]);

# t_exec_pb[p,b] : tiempo de ejecucion del lote b si lo hace el picker p.
#                  Ya NO es variable de decision: es un dato derivado.
param t_exec_pb[<p,b> in P * B] :=
    tiempo_fijo[b] + R_b[b] / V_p[p];

# PB_elig : combinaciones (picker, lote) que cumplen la restriccion de frio.
#           Si un lote queda sin NINGUN picker elegible, el batching de la
#           etapa previa genero un lote inviable para congelados: hay que
#           detectarlo ANTES de resolver (ver chequeo mas abajo), no dejar
#           que el solver devuelva "infactible" sin mas explicacion.
#           Tolerancia +1e-9: misma que usan models/opp_hc_4 y
#           models/opp_aco_4 para el mismo chequeo (y que ya usaba
#           models/opp_v5_2_split/utils/cold_chain_validation.py, que replica este
#           set en Python) -- antes esta linea comparaba con <= estricto,
#           sin margen, mientras esos otros si lo tenian (hallazgo de
#           auditoria 2026-09-10): un t_exec_pb == T_frio_max con error de
#           redondeo de punto flotante podia quedar afuera de PB_elig aca
#           pero adentro en los otros modulos, para el mismo dato.
set PB_elig := { <p,b> in P * B with t_exec_pb[p,b] <= T_frio_max + 1e-9 };

# Chequeo de factibilidad basica: lotes sin ningun picker elegible.
# (si esta lista no esta vacia, el modelo va a dar infactible seguro)
set B_sin_picker_elegible := { <b> in B with (sum <p> in P with <p,b> in PB_elig: 1) == 0 };


##############################################################################
# VARIABLES
##############################################################################

# x_pb[p,b] : 1 si el lote b es asignado al picker p (solo pares elegibles)
var x_pb[PB_elig] binary;

# c_pb[p,b] : tiempo de completitud del lote b en la agenda del picker p
var c_pb[PB_elig] >= 0;

# c_b[b] : tiempo de completitud del lote b (independiente del picker)
var c_b[B] >= 0;

# y_bk[b,k] : 1 si, en el picker que comparten, el lote b va antes que el k
var y_bk[<b,k> in B * B with b < k] binary;

# ta_n[n] / ea_n[n] : tardanza / adelanto de la orden n
var ta_n[N] >= 0;
var ea_n[N] >= 0;


##############################################################################
# OBJECTIVE
##############################################################################

minimize obj:
      W_full  * (sum <b> in B: c_b[b])
    + W_ea_ta * (  W_ea * (sum <n> in N: ea_n[n])
                 + W_ta * (sum <n> in N: ta_n[n])
                );


##############################################################################
# CONSTRAINTS
##############################################################################

#################### Asignacion (solo pares elegibles por frio) ##############

subto assign_exactly_one_picker:
    forall <b> in B:
        sum <p> in P with <p,b> in PB_elig:
            x_pb[p,b] == 1;

##################### Tiempo de completitud (sin Big-M) #######################

# Antes esto eran DOS restricciones con Big-M (d_b variable). Ahora
# t_exec_pb es un numero conocido, asi que "si X=1, c_pb >= t_exec" es
# directamente lineal: no hace falta linealizar nada.
subto batch_completion_floor:
    forall <p,b> in PB_elig:
        t_exec_pb[p,b] * x_pb[p,b] <= c_pb[p,b];

subto c_b_lower_bound:
    forall <p,b> in PB_elig:
        c_pb[p,b] - M * (1 - x_pb[p,b]) <= c_b[b];

###################### Secuenciamiento sin solapamiento #######################
# OJO: antes se usaba d_b[k] (igual para cualquier picker). Ahora que
# la velocidad depende del picker, hay que usar t_exec_pb[p,k].

subto non_overlap_1:
    forall <p> in P:
        forall <b,k> in B * B with b < k and <p,b> in PB_elig and <p,k> in PB_elig:
            c_pb[p,k] >= c_pb[p,b] + t_exec_pb[p,k]
                         - M_seq * (3 - x_pb[p,b] - x_pb[p,k] - y_bk[b,k]);

subto non_overlap_2:
    forall <p> in P:
        forall <b,k> in B * B with b < k and <p,b> in PB_elig and <p,k> in PB_elig:
            c_pb[p,b] >= c_pb[p,k] + t_exec_pb[p,b]
                         - M_seq * (2 - x_pb[p,b] - x_pb[p,k] + y_bk[b,k]);

########################### Earliness y tardiness #############################
# Filtradas por Bn[n,b]==1: antes se generaba una fila por cada (p,b,n) sin
# importar si el pedido n estaba en el lote b (siempre no-binding si no).

subto tardiness_definition:
    forall <p,b,n> in P * B * N with Bn[n,b] == 1 and <p,b> in PB_elig:
        c_pb[p,b] - Dd[n] - M * (2 - x_pb[p,b] - Bn[n,b]) <= ta_n[n];

# subto tardiness_definition:
#     forall <b,n> in B * N with Bn[n,b] == 1:
#         c_b[b] - Dd[n] <= ta_n[n];

subto earliness_definition:
    forall <p,b,n> in P * B * N with Bn[n,b] == 1 and <p,b> in PB_elig:
        Dd[n] - c_pb[p,b] - M * (2 - x_pb[p,b] - Bn[n,b]) <= ea_n[n];

# subto earliness_definition:
#     forall <b,n> in B * N with Bn[n,b] == 1:
#         Dd[n] - c_b[b] <= ea_n[n]

############### (Opcional) limite de frio incluyendo espera/despacho ##########
# Si ademas del tiempo de armado importa cuanto tiempo pasa el lote ya
# armado hasta que se despacha (c_b), descomentar y ajustar:
#
# param T_despacho_max := read "../dat_files/despacho.dat" as "1n" comment "#";
# subto cold_chain_dispatch:
#     forall <b> in B:
#         c_b[b] <= T_despacho_max;

from helpers import injector
import services
import sims4.commands
import sims4.log
from sims.sim_spawner import SimSpawner
from sims.sim_info_types import Gender

logger = sims4.log.Logger('julie', default_owner='julie')

# Not that when injecting to cls function, if cls is not used in that function,
# it is not passed in *args.
@injector.inject_to(SimSpawner, 'spawn_sim')
def _override_spawn_sim(original, *args, **kwargs):
    logger.info("julie enter")
    result = original(*args, **kwargs)

    try:
        if result:
            logger.info("julie, args {}, kwargs {}", args, kwargs)
            if not args:
                return result
            sim_info = args[0]
            logger.info("julie, sim_info {}", sim_info)

    except Exception as e:
        logger.exception(
            "julie SimSpawner.spawn_sim injection failed to run, err {}",
            str(e))

    logger.info("julie end.")
    return result

@sims4.commands.Command('getpopulation', command_type=sims4.commands.CommandType.Live)
def getpop(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    allSims = services.sim_info_manager().get_all()
    allCnt = len(allSims)
    maleCnt = 0
    for simInfo in allSims:
        if (simInfo.gender == Gender.MALE):
            maleCnt += 1
            
    output('Your town\'s population is {}, male {}, female {}.'.format(
        allCnt, maleCnt, allCnt - maleCnt))

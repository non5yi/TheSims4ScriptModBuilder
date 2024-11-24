from helpers import injector
import sims4.log
from sims.sim_spawner import SimSpawner

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

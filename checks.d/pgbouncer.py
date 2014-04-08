# pgbouncer agent check for DataDog.
# Based on the postgres agent check, written by steinn@plainvanillagames.com
from checks import AgentCheck, CheckException

class pgBouncer(AgentCheck):
    """Collects pgbouncer statistics
    """

    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.connection = None
        self.pools = []
        self.versions = {}

    def _collect_pool_stats(self, db, pools, tags):
        query = "SHOW POOLS";
        _pool_fields = ['database','user','cl_active','cl_waiting','sv_active','sv_idle','sv_used','sv_tested','sv_login','maxwait']
        cursor = db.cursor()
        cursor.execute(query)
        for row in [dict(zip(_pool_fields, row)) for row in cursor.fetchall()]:
            if row['database'] not in pools:
                continue
            # using gauge here because 0 does not elicit a rate() call!
            metric_tags = tags + ["pbouncer_pool:{}".format(row['database'])]
            self.gauge('pgbouncer.cl_active', row['cl_active'], tags=metric_tags)
            self.gauge('pgbouncer.cl_waiting', row['cl_waiting'], tags=metric_tags)
            self.gauge('pgbouncer.maxwait', row['maxwait'], tags=metric_tags)
            self.gauge('pgbouncer.sv_active', row['sv_active'], tags=metric_tags)

    def get_connection(self, host, port, user, password):
        "Get and memoize connection to pgbouncer"
        if self.connection is not None:
            return self.connection

        dbname = "pgbouncer"
        if host != "" and user != "":
            try:
                import psycopg2 as pg
            except ImportError:
                raise ImportError("psycopg2 library cannot be imported. Please check the installation instruction on the Datadog Website.")
            
            if port != '':
                connection = pg.connect(host=host, port=port, user=user, password=password, database=dbname)
            else:
                connection = pg.connect(host=host, user=user, password=password, database=dbname)
            connection.autocommit = True  # pgbouncer special db does not 
        else:
            if not host:
                raise CheckException("Please specify a pgbouncer host to connect to.")
            elif not user:
                raise CheckException("Please specify a user to connect to Postgres as.")
        self.connection = connection
        return connection


    def check(self, instance):
        host = instance.get('host', '')
        port = instance.get('port', '')
        user = instance.get('username', '')
        password = instance.get('password', '')
        pools = instance.get('pools', [])
        tags = instance.get('tags', [])

        db = self.get_connection(host, port, user, password)

        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if tags is None:
            tags = []
        
        # Collect metrics
        self._collect_pool_stats(db, pools, tags)


